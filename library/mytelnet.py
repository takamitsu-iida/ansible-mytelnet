#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=C0111,E0611

# (c) 2018, Takamitsu IIDA (@takamitsu-iida)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'metadata_version': '1.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: mytelnet
short_description: Executes a low-down and dirty telnet command
version_added: 2.6
description:
  - Executes a low-down and dirty telnet command
  - This is mostly to be used for enabling ssh on devices that only have telnet enabled by default.
options:
  commands:
    description:
      - List of commands to be executed in the telnet session.
    required: True
  network_os:
    description:
      - network os type
    default: ios
  host:
    description:
      - The target host ip address(dns name)
    required: True
  port:
    description:
      - The remote port
    default: 23
  user:
    description:
      - The user for login
  password:
    description:
      - The password for login
  become:
    description:
      - Need privilege escalation or not
    default: False
  become_pass:
    description:
      - The password for privilege escalation
  connect_timeout:
    description:
      - timeout for telnet to be connected
    default: 10
  login_timeout:
    description:
      - timeout for login prompt
    default: 5
  command_timeout:
    description:
      - timeout for command prompt
    default: 5
  pause:
    description:
      - Seconds to pause between each command issued
    default: 1

author:
  - Takamitsu IIDA (@takamitsu-iida)
'''

EXAMPLES = '''
- name: send commands
  delegate_to: localhost
  mytelnet:
    host: "{{ ansible_host }}"
    network_os: "{{ ansible_network_os }}"
    user: "{{ ansible_user }}"
    password: "{{ ansible_ssh_pass }}"
    become: "{{ ansible_become }}"
    become_pass: "{{ ansible_become_pass }}"
    commands:
      - show process cpu | inc CPU
      - show ip int brief
  register: r

- hosts:
  tr1 ansible_host=172.28.128.3

- group_vars:
  ansible_network_os: ios
  ansible_user: cisco
  ansible_ssh_pass: cisco
  ansible_become: yes
  ansible_become_method: enable
  ansible_become_pass: cisco
'''

RETURN = '''
stdout:
  description: The set of responses from the commands
  type: list
  returned: always
  sample: [ '...', '...' ]

stdout_lines:
  description: The value of stdout split into a list
  type: list
  returned: always
  sample: [ ['...', '...'], ['...'], ['...'] ]
'''

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import string_types

from ansible.module_utils.mytelnet_util import login, logout, run_commands


def to_lines(stdout):
  for item in stdout:
    if isinstance(item, string_types):
      item = str(item).split('\n')
    yield item


def main():
  """main entry point for module execution
  """
  argument_spec = dict(
    commands=dict(type='list', required=True),
    network_os=dict(default='ios', type='str'),
    host=dict(type='str', required=True),
    port=dict(default=23, type='int'),
    user=dict(default="", type='str'),
    password=dict(default="", type='str'),
    become=dict(default=False, type='bool'),
    become_pass=dict(default="", type='str'),
    connect_timeout=dict(default=10, type='int'),
    login_timeout=dict(default=5, type='int'),
    command_timeout=dict(default=5, type='int'),
    pause=dict(default=1, type='int'),
    mode=dict(default='telnet', type='str')
    )

  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

  try:
    login(module)
    responses = run_commands(module)
    logout(module)
  except EOFError as e:
    module.fail_json(msg='Telnet action failed: %s' % to_text(e))

  result = {
    'changed': False,
    'stdout': responses,
    'stdout_lines': list(to_lines(responses))
  }

  # for debug purpose
  result.update({
    'prompt_history': module.prompt_history,
    'command_history': module.command_history,
    'raw_outputs': module.raw_outputs
  })

  module.exit_json(**result)


if __name__ == '__main__':
  main()
