# -*- coding: utf-8 -*-
# pylint: disable=W0611,C0111,C0412

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

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action.normal import ActionModule as _ActionModule

try:
  from __main__ import display
except ImportError:
  from ansible.utils.display import Display
  display = Display()


class ActionModule(_ActionModule):

  def run(self, tmp=None, task_vars=None):
    del tmp  # tmp no longer has any effect

    # self._play_contextから情報を取り出しても踏み台を踏んだときはうまくいかない
    #
    # display.v(str(self._play_context.remote_user))  #=> bastion
    # display.v(str(self._play_context.remote_addr))  #=> 10.35.158.20
    # display.v(str(self._play_context.password))     #=> None
    # display.v(str(self._play_context.become))       #=> #False
    # display.v(str(self._play_context.become_pass))  #=> None

    # hostvarsを取り出す
    #
    inventory_hostname = task_vars.get('inventory_hostname')
    hostvars = task_vars['hostvars'].get(inventory_hostname)

    #
    # hostvarsから情報を取り出す
    #
    remote_addr = hostvars.get('remote_addr') or hostvars.get('ansible_ssh_host') or hostvars.get('ansible_host')
    # port = hostvars.get('port') or hostvars.get('ansible_ssh_port') or hostvars.get('ansible_port', 23)
    remote_user = hostvars.get('remote_user') or hostvars.get('ansible_ssh_user') or hostvars.get('ansible_user')
    password = hostvars.get('password') or hostvars.get('ansible_ssh_pass') or hostvars.get('ansible_password') or hostvars.get('ansible_pass') # ansible_pass is wrong setting
    become = hostvars.get('become') or hostvars.get('ansible_become', False)
    become_pass = hostvars.get('become_pass') or hostvars.get('ansible_become_password') or hostvars.get('ansible_become_pass')
    network_os = hostvars.get('ansible_network_os')
    # display.v(remote_addr)
    # display.v(port)
    # display.v(remote_user)
    # display.v(password)
    # display.v(str(become))
    # display.v(become_pass)
    # display.v(network_os)

    #
    # self._task.argsに不足があれば追加する
    #

    # mytelnetモジュールの引数は以下の通り。
    # これらのうちhostやpassword等はインベントリに設定するのでそこから持ってきたほうがよい。
    # argument_spec = dict(
    #   commands=dict(type='list', required=True),
    #   network_os=dict(default='ios', type='str'),
    #   host=dict(type='str', required=True),
    #   port=dict(default=23, type='int'),
    #   user=dict(default="", type='str'),
    #   password=dict(default="", type='str'),
    #   become=dict(default=False, type='bool'),
    #   become_pass=dict(default="", type='str'),
    #   connect_timeout=dict(default=10, type='int'),
    #   login_timeout=dict(default=5, type='int'),
    #   command_timeout=dict(default=5, type='int'),
    #   pause=dict(default=1, type='int')
    #   )
    if not self._task.args.get('host') and remote_addr:
      self._task.args['host'] = remote_addr

    if not self._task.args.get('port') or self._task.args.get('port') == 22:
      self._task.args['port'] = 23

    if not self._task.args.get('user') and remote_user:
      self._task.args['user'] = remote_user

    if not self._task.args.get('password') and password:
      self._task.args['password'] = password

    if not self._task.args.get('become') and become:
      self._task.args['become'] = become

    if not self._task.args.get('become_pass') and become_pass:
      self._task.args['become_pass'] = become_pass

    if not self._task.args.get('network_os') and network_os:
      self._task.args['network_os'] = network_os

    result = super(ActionModule, self).run(task_vars=task_vars)
    return result
