# -*- coding: utf-8 -*-
# pylint: disable=W0212,E0611,C0111
# W0212:Access to a protected member _role of a client class
# E0611:No name 'urllib' in module '_MovedItems'
# C0111:Missing class docstring

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


import os
import re
import time

from ansible.plugins.action.normal import ActionModule as _ActionModule

try:
  # pylint: disable=W0611
  # W0611:Unused display imported from __main__
  from __main__ import display
except ImportError:
  # pylint: disable=C0412
  # C0412:Imports from package ansible are not grouped
  from ansible.utils.display import Display
  display = Display()


PRIVATE_KEYS_RE = re.compile('__.+__')


class ActionModule(_ActionModule):

  def get_working_path(self):
    cwd = self._loader.get_basedir()
    if self._task._role is not None:
      cwd = self._task._role._role_path
    return cwd


  def write_log(self, hostname, contents):
    log_path = self.get_working_path() + '/log'
    if not os.path.exists(log_path):
      os.mkdir(log_path)
    # tstamp = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))
    tstamp = time.strftime("%Y-%m-%d@%H-%M-%S", time.localtime(time.time()))
    filename = '{0}/{1}_{2}.log'.format(log_path, hostname, tstamp)
    open(filename, 'w').write(contents)

    return filename


  def run(self, tmp=None, task_vars=None):
    del tmp  # tmp no longer has any effect

    #
    # pre process
    #

    # self._play_contextから情報を取り出しても踏み台を踏んだときはうまくいかない
    #
    # display.v(str(self._play_context.remote_user))  #=> bastion
    # display.v(str(self._play_context.remote_addr))  #=> 10.35.158.20
    # display.v(str(self._play_context.password))     #=> None
    # display.v(str(self._play_context.become))       #=> #False
    # display.v(str(self._play_context.become_pass))  #=> None

    if not hasattr(self._play_context, 'delegate_to'):
      return dict(failed=True, msg='mytelnet module require delegate_to directive but not set')

    # hostvarsを取り出す
    #
    inventory_hostname = task_vars.get('inventory_hostname')
    hostvars = task_vars['hostvars'].get(inventory_hostname)

    #
    # hostvarsから情報を取り出す
    #
    remote_addr = hostvars.get('remote_addr') or hostvars.get('ansible_ssh_host') or hostvars.get('ansible_host')
    port = hostvars.get('port') or hostvars.get('ansible_ssh_port') or hostvars.get('ansible_port', 23)
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

    if not self._task.args.get('port') and port:
      self._task.args['port'] = port
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

    #
    # run module
    #

    result = super(ActionModule, self).run(task_vars=task_vars)

    #
    # post process
    #

    if self._task.args.get('log') and result.get('__log__'):
      log_path = self.write_log(inventory_hostname, result['__log__'])
      result['log_path'] = log_path
      del result['__log__']

    return result
