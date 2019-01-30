# mytelnetモジュール

Ansible2.4からコアモジュールに含まれるようになったtelnetモジュールは、
マニュアルに記載の通りsshが有効になってない機器に乗り込んでsshを初期設定するのが主な利用シーンなので、
高度なことを期待してはいけないのですが・・・

delegate_toを使っての踏み台経由のtelnetが動かないので大変困ってしまいました。

設定で回避するとかそんなレベルではなさそうでしたので、本家のtelnetモジュールの利用は諦めて改めてモジュールを作成しました。

<br><br>

# ファイル構成

```text
.
├── LICENSE
├── README.md
├── ansible.cfg
├── console.yml
├── inventories
│   ├── development
│   │   ├── group_vars
│   │   │   ├── all.yml
│   │   │   ├── bastion.yml
│   │   │   ├── console_routers.yml
│   │   │   └── telnet_routers.yml
│   │   ├── host_vars
│   │   └── hosts
│   └── mac
│       ├── group_vars
│       │   └── telnet_routers.yml
│       ├── host_vars
│       └── hosts
├── library
│   └── mytelnet.py
├── module_utils
│   ├── mytelnet_util.py
│   └── telnetlib.py
├── mytelnet.yml
├── plugins
│   └── action
│       └── mytelnet.py
└── vscode.code-workspace
```

<br><br>

# ansible.cfg

自作のモジュールはlibraryフォルダに、module_utilsはmodule_utilsに配置するように設定します。

またactionプラグインを使ってインベントリ情報を吸い上げていますので、そのパスも必要です。

```ini
[defaults]

library = ./library

module_utils = ./module_utils

action_plugins = ./plugins/action
```

<br><br>

# hosts ファイル

hostsファイルではIPアドレスを設定しておきます。

```ini
#
# for mac environment
#

#
# ルータ
#
[telnet_routers]
tr1 ansible_host=172.28.128.3
```

<br><br>

# group_vars ファイル

接続に必要な設定情報をgroup_varsかhost_varsに設定します。

`ansible_connection` は設定しないでください。

```yml
---
ansible_ssh_common_args: ""

ansible_network_os: ios
ansible_user: cisco
ansible_password: cisco
ansible_become: yes
ansible_become_method: enable
ansible_become_pass: cisco
```

<br><br>

# プレイブック

commands配列はios_commandモジュールと同じ方法で設定します。

delegate_toは必須です。localhostもしくは踏み台になるサーバを指定してください。

network_osは'ios'のみ認識します。
'ios'の場合はterminal length 0の設定とenable処理を自動で行います。
'ios'ではない装置の場合はそのへんの処理をコマンドとして打ち込んでください。

```yml
---
# 設定パラメータ
#
# command ---  コマンドの配列
# networkos --- 装置種別（デフォルトはiosで、現在のところiosしか試していない）
# host --- ターゲットのアドレス
# port --- ポート番号（デフォルトは23）
# user --- ユーザ名
# password --- パスワード
# become --- 管理者モードになるか
# become_pass --- 管理者モードのパスワード

# タスク設定
# delegate_toは必須。localhostもしくは踏み台を指定すること。

# 戻り値
# stdout 配列。送り込んだコマンド配列に対応して格納される。

# 禁止パラメータ
# ansible_connection: network_cli
# これが設定されていると動作しない

- name: execute command on cisco devices
  hosts: tr1  # telnet_routers
  gather_facts: False
  strategy: linear  # free
  serial: 0

  tasks:

    - name: send commands
      # no_log: True
      delegate_to: localhost
      mytelnet:
        # これらはインベントリに設定していれば自動設定されるので不要
        # network_os: "{{ ansible_network_os }}"
        # host: "{{ ansible_host }}"
        # user: "{{ ansible_user }}"
        # port: "{{ ansible_port }}"
        # password: "{{ ansible_password }}"
        # become: "{{ ansible_become }}"
        # become_pass: "{{ ansible_become_pass }}"
        commands:
          - command: clear counters gig 2
            prompt: '\[confirm\]'
            answer: y
          - show run int gig 2
          - show process cpu | inc CPU
      register: r

    - name: show stdout
      debug:
        msg: |
          {% for s in r.stdout %}
          {{ s }}
          -----
          {% endfor %}

    - name: command history (for debug purpose)
      debug: var=r.command_history

    - name: prompt history (for debug purpose)
      debug: var=r.prompt_history
```

# 実行例

csr1000vをターゲットに実行した例です。

```bash
iida-macbook-pro:ansible-mytelnet iida$ ansible-playbook mytelnet.yml

PLAY [execute command on cisco devices] ***********************************************************************************

TASK [send commands] ******************************************************************************************************
 [WARNING]: Module did not set no_log for password

 [WARNING]: Module did not set no_log for become_pass

ok: [tr1 -> localhost]

TASK [show stdout] ********************************************************************************************************
ok: [tr1] => {}

MSG:

csr#
-----
Building configuration...

Current configuration : 99 bytes
!
interface GigabitEthernet2
 ip address dhcp
 negotiation auto
 no mop enabled
 no mop sysid
end

-----
CPU utilization for five seconds: 0%/0%; one minute: 0%; five minutes: 0%
-----



TASK [command history (for debug purpose)] ********************************************************************************
ok: [tr1] => {
    "r.command_history": [
        "terminal length 0",
        "terminal width 512",
        "enable",
        "cisco",
        "clear counters gig 2",
        "y",
        "show run int gig 2",
        "show process cpu | inc CPU",
        "quit"
    ]
}

TASK [prompt history (for debug purpose)] *********************************************************************************
ok: [tr1] => {
    "r.prompt_history": [
        "Username:",
        "Password:",
        "csr>",
        "Password:",
        "csr#",
        "[confirm]",
        "csr#"
    ]
}

PLAY RECAP ****************************************************************************************************************
tr1                        : ok=4    changed=0    unreachable=0    failed=0

iida-macbook-pro:ansible-mytelnet iida$
```

<br><br>

# コンソールサーバを使う場合

インベントリ

```ini
[console_routers]
cr12 ansible_host=10.35.185.2 ansible_port=2011
```

group_vars

```yml
---

# 設定しないこと
# ansible_connection: network_cli

ansible_network_os: ios
ansible_become: yes
ansible_become_method: enable
ansible_become_pass: cisco
```

プレイブック

```yml
---
#
# コンソールサーバ経由でコマンドを打ち込みます
#
# 2018/08/02 初版
#
# Takamitsu IIDA (@takamitsu-iida)

- name: execute command on cisco devices
  hosts: cr12
  gather_facts: False

  tasks:

    - name: send commands
      # no_log: True
      delegate_to: localhost
      mytelnet:
        mode: console
        commands:
          - show version
          - show process cpu | inc CPU
      register: r

    - name: show stdout
      debug:
        msg: |
          {% for s in r.stdout %}
          -----
          {{ s }}
          -----
          {% endfor %}

    - name: command history (for debug purpose)
      debug: var=r.command_history

    - name: prompt history (for debug purpose)
      debug: var=r.prompt_history

```

実行例。

```bash
iida-macbook-pro:ansible-mytelnet iida$ ansible-playbook console.yml

PLAY [execute command on cisco devices] **************************************************

TASK [send commands] *********************************************************************
 [WARNING]: Module did not set no_log for become_pass

 [WARNING]: Module did not set no_log for password

ok: [cr12 -> localhost]

TASK [show stdout] ***********************************************************************
ok: [cr12] => {}

MSG:

-----
Cisco IOS Software, C181X Software (C181X-ADVIPSERVICESK9-M), Version 15.1(4)M12a, RELEASE SOFTWARE (fc1)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2016 by Cisco Systems, Inc.
Compiled Tue 04-Oct-16 02:58 by prod_rel_team

ROM: System Bootstrap, Version 12.3(8r)YH6, RELEASE SOFTWARE (fc1)

r12 uptime is 3 days, 2 hours, 57 minutes
System returned to ROM by reload at 12:04:13 UTC Mon Jan 2 2006
System restarted at 11:59:51 UTC Mon Jan 2 2006
System image file is "flash:c181x-advipservicesk9-mz.151-4.M12a.bin"
Last reload type: Normal Reload


This product contains cryptographic features and is subject to United
States and local country laws governing import, export, transfer and
use. Delivery of Cisco cryptographic products does not imply
third-party authority to import, export, distribute or use encryption.
Importers, exporters, distributors and users are responsible for
compliance with U.S. and local country laws. By using this product you
agree to comply with applicable laws and regulations. If you are unable
to comply with U.S. and local laws, return this product immediately.

A summary of U.S. laws governing Cisco cryptographic products may be found at:
http://www.cisco.com/wwl/export/crypto/tool/stqrg.html

If you require further assistance please contact us by sending email to
export@cisco.com.

Cisco 1812-J (MPC8500) processor (revision 0x400) with 236544K/25600K bytes of memory.
Processor board ID FHK113718U0, with hardware revision 0000

10 FastEthernet interfaces
1 ISDN Basic Rate interface
1 Virtual Private Network (VPN) Module
31360K bytes of ATA CompactFlash (Read/Write)


License Info:

License UDI:

-------------------------------------------------
Device#	  PID			SN
-------------------------------------------------
*0  	  CISCO1812-J/K9        FHK113718U0



Configuration register is 0x2102
-----
-----
CPU utilization for five seconds: 0%/0%; one minute: 0%; five minutes: 0%
-----



TASK [command history (for debug purpose)] ***********************************************
ok: [cr12] => {
    "r.command_history": [
        "terminal length 0",
        "terminal width 512",
        "enable",
        "cisco",
        "show version",
        "show process cpu | inc CPU",
        "quit"
    ]
}

TASK [prompt history (for debug purpose)] ************************************************
ok: [cr12] => {
    "r.prompt_history": [
        "r12>",
        "Password:",
        "r12#"
    ]
}

PLAY RECAP *******************************************************************************
cr12                       : ok=4    changed=0    unreachable=0    failed=0

iida-macbook-pro:ansible-mytelnet iida$
```

<br><br>

# 2019/01/30 追記

Ciscoのshow techのような大きなデータを受信すると、TCP Zero Windowが発生して受信できないことがあります。
これを避けるためにPythonのtelnetlib.pyを内部に取り込み、書き換えを行っています。

```text
iida-macbook-pro:module_utils iida$ diff telnetlib.py ~/.pyenv/versions/3.6.4/lib/python3.6/telnetlib.py
524,525c524
<         # buf = self.sock.recv(50)
<         buf = self.sock.recv(15000)  # fixed by takamitsu-iida 20190130, this shoud be large enough to receive cisco show-tech output.
---
>         buf = self.sock.recv(50)
```
