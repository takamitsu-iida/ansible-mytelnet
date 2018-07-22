# mytelnetモジュール

Ansible2.4からコアモジュールに含まれるようになったtelnetモジュールは、マニュアルに記載の通りsshが有効になってない機器に乗り込んでsshを初期設定するのが主な利用シーンなので、高度なことを期待してはいけないのですが・・・

本家のtelnetモジュールはpython3で動きませんし、なによりdelegate_toを使っての踏み台経由のtelnetが動かないので大変困ってしまいました。

設定で回避するとかそんなレベルではなさそうでしたので、本家のtelnetモジュールの利用は諦めて改めてモジュールを作成しました。

<br><br>

# ファイル構成

```bash
.
├── LICENSE
├── README.md
├── ansible.cfg
├── inventories
│   ├── development
│   │   ├── group_vars
│   │   │   └── telnet_routers.yml
│   │   ├── host_vars
│   │   └── hosts
│   └── mac
│       ├── group_vars
│       │   └── telnet_routers.yml
│       ├── host_vars
│       └── hosts
├── library
│   ├── module_utils
│   │   └── mytelnet_util.py
│   └── mytelnet.py
├── log
├── mytelnet.yml
└── vscode.code-workspace
```

<br><br>

# ansible.cfg

自作のモジュールはlibraryフォルダに、module_utilsはlibrary/module_utilsに配置するように設定します。

```ini
[defaults]

library = ./library

module_utils = ./library/module_utils
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
キー名はプレイブック側で参照しやすいものであれば何でも構いません。

```yml
---
ansible_ssh_common_args: ""

ansible_network_os: ios
ansible_user: cisco
ansible_ssh_pass: cisco
ansible_become: yes
ansible_become_method: enable
ansible_become_pass: cisco
```

<br><br>

# プレイブック

接続方法にnetwork_cliを使えるわけではないので、mytelnetモジュールに接続先やユーザ名、パスワードを個別に渡さなければいけません。それら値はgroup_varsやhost_varsで定義したものを引っ張ってくればいいでしょう。

commands配列はios_commandモジュールと同じ方法で設定します。

delegate_toは必須です。localhostもしくは踏み台になるサーバを指定してください。

network_osは'ios'のみ認識します。'ios'の場合はenable処理を自動でやっているのと、最後の切断処理で'quit'を打ち込んでいます。'ios'ではない装置の場合は適当な文字列を設定してください。

```yml
---
#
# Ciscoルータにコマンドを打ち込みます
#
# 2018/07/10 初版
#
# Takamitsu IIDA (@takamitsu-iida)

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
#
# 戻り値は stdout 配列。送り込んだコマンド配列に対応して格納される。

- name: execute command on cisco devices
  hosts: tr1
  gather_facts: False
  strategy: linear  # free
  serial: 0

  tasks:

    - name: send commands
      # no_log: True
      delegate_to: localhost
      mytelnet:
        host: "{{ ansible_host }}"
        network_os: "{{ ansible_network_os }}"
        user: "{{ ansible_user }}"
        password: "{{ ansible_ssh_pass }}"
        become: "{{ ansible_become }}"
        become_pass: "{{ ansible_become_pass }}"
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
