# mytelnetモジュール

Ansible2.4からコアモジュールに含まれるようになったtelnetモジュールは、マニュアルに記載の通りsshが有効になってない機器に乗り込んでsshを初期設定するのが主な利用シーンなので、高度なことを期待してはいけないのですが・・・

本家のtelnetモジュールはpython3で動きませんし、なによりdelegate_toを使っての踏み台経由のtelnetが動かないので大変困ってしまいました。

設定で回避するとかそんなレベルではなさそうでしたので、本家のtelnetモジュールの利用は諦めて改めてモジュールを作成しました。

<br><br>

# ファイル構成

```bash
.
├── README.md
├── ansible.cfg
├── inventories
│   └── mac
│       ├── group_vars
│       │   └── telnet_routers.yml
│       ├── host_vars
│       └── hosts
├── library
│   └── mytelnet.py
├── module_utils
│   └── mytelnet_util.py
├── mytelnet.yml
├── plugins
│   └── action
│       └── mytelnet.py
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
        # これらはインベントリから自動設定されるので不要
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
