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

# telnetlib doc
# https://docs.python.jp/3/library/telnetlib.html

import re
import telnetlib
from time import sleep

from ansible.module_utils._text import to_text, to_bytes
from ansible.module_utils.network.common.utils import to_list


def get_raw_outputs(module):
  if hasattr(module, 'raw_outputs'):
    return module.raw_outputs
  module.raw_outputs = list()
  return module.raw_outputs


def add_raw_outputs(module, output):
  get_raw_outputs(module).append(output)


def get_command_history(module):
  if hasattr(module, 'command_history'):
    return module.command_history
  module.command_history = list()
  return module.command_history


def add_command_history(module, cmd):
  get_command_history(module).append(cmd)


def get_prompt(module):
  if hasattr(module, 'prompt'):
    return module.prompt
  module.prompt = ""
  return module.prompt


def get_prompt_history(module):
  if hasattr(module, 'prompt_history'):
    return module.prompt_history
  module.prompt_history = list()
  return module.prompt_history


def add_prompt_history(module, prompt):
  current_prompt = get_prompt(module)
  if current_prompt == prompt:
    return
  get_prompt_history(module).append(prompt)
  module.prompt = prompt


def get_command_timeout(module):
  if hasattr(module, 'command_timeout'):
    return module.command_timeout
  module.command_timeout = module.params['command_timeout']
  return module.command_timeout


def get_command_prompts(module):
  if hasattr(module, 'command_prompts'):
    return module.command_prompts
  module.command_prompts = list()
  module.command_prompts.append(re.compile(br"[\r\n]?[\w\+\-\.:\/\[\]]+(?:\([^\)]+\)){0,3}(?:[>#]) ?$"))
  return module.command_prompts


def get_login_prompts(module):
  if hasattr(module, 'login_prompts'):
    return module.login_prompts
  module.login_prompts = list()
  module.login_prompts.append(re.compile(br"[Ll]ogin: ?|[Uu]sername: ?"))
  return module.login_prompts


def get_password_prompts(module):
  if hasattr(module, 'password_prompts'):
    return module.password_prompts
  module.password_prompts = list()
  module.password_prompts.append(re.compile(br"[\r\n](?:Local_)?[Pp]assword: ?$"))
  return module.password_prompts


def get_connection(module):
  if hasattr(module, 'connection'):
    return module.connection

  host = module.params['host']
  port = module.params['port']
  connect_timeout = module.params['connect_timeout']

  # try to connect target host using telnetlib.Telnet
  try:
    tn = telnetlib.Telnet(host, port=port, timeout=connect_timeout)
  except OSError as e:
    module.fail_json(msg='Failed to connect target host: %s' % to_text(e))

  module.connection = tn
  return module.connection


def login(module):
  """Login to the target host.
  """
  tn = get_connection(module)

  user = module.params['user']
  password = module.params['password']
  login_timeout = module.params['login_timeout']

  command_prompts = get_command_prompts(module)
  login_prompts = get_login_prompts(module)
  password_prompts = get_password_prompts(module)

  try:
    if user:
      index, match, out = tn.expect(login_prompts, login_timeout)
      if index < 0:
        tn.close()
        module.fail_json(msg='Failed to expect login prompt: %s' % to_text(out))
      matched_prompt = match.group().strip()
      add_prompt_history(module, matched_prompt)
      add_raw_outputs(module, out)
      tn.write(to_bytes('%s\r' % user))

    if password:
      index, match, out = tn.expect(password_prompts, login_timeout)
      if index < 0:
        tn.close()
        module.fail_json(msg='Failed to expect password prompt: %s' % to_text(out))
      matched_prompt = match.group().strip()
      add_prompt_history(module, matched_prompt)
      add_raw_outputs(module, out)
      tn.write(to_bytes('%s\r' % password))

    # wait for command prompt
    index, match, out = tn.expect(command_prompts, login_timeout)
    if index < 0:
      tn.close()
      module.fail_json(msg='Wrong password or failed to expect prompt: %s' % to_text(out))
    matched_prompt = match.group().strip()
    add_prompt_history(module, matched_prompt)
    add_raw_outputs(module, out)

    on_login(module)
    on_become(module)

  except EOFError as e:
    if tn:
      tn.close()
    module.fail_json(msg='Telnet action failed: %s' % to_text(e))


def on_login(module):
  network_os = module.params['network_os']
  if network_os == 'ios':
    send_and_wait(module, 'terminal length 0')
    send_and_wait(module, 'terminal width 512')


def on_become(module):
  if get_prompt(module).endswith(b'#'):
    return

  if not module.params['become']:
    return

  passwd = module.params['become_pass']
  if passwd:
    network_os = module.params['network_os']
    if network_os == 'ios':
      # in case of ios, send 'enable' and wait for Password:
      send_and_wait(module, 'enable', prompt='[Pp]assword: ?', answer=passwd)
      prompt = get_prompt(module)
      if not prompt or not prompt.endswith(b'#'):
        get_connection(module).close()
        module.fail_json(msg='failed to elevate privilege to enable mode still at prompt [%s]' % prompt)


def logout(module):
  """Logout from the host.
  """
  tn = get_connection(module)

  network_os = module.params['network_os']
  if network_os == 'ios':
    send_command(module, 'quit')

  tn.close()


def send_command(module, command):
  tn = get_connection(module)
  tn.write(to_bytes('%s\r' % command))
  add_command_history(module, command)


def send_and_wait(module, command, prompt=None, answer=None):
  """Send a command and wait for prompts
  """
  tn = get_connection(module)
  prompts = get_command_prompts(module)
  command_timeout = get_command_timeout(module)

  try:
    send_command(module, command)

    if prompt:
      index, match, out = tn.expect([to_bytes(prompt)], command_timeout)
      if index < 0:
        tn.close()
        module.fail_json(msg='Failed to expect prompt: %s : %s' % (command, prompt))
      matched_prompt = match.group().strip()
      add_prompt_history(module, matched_prompt)
      add_raw_outputs(module, out)

      if answer:
        send_command(module, answer)
        # in case of no output like this, we need to wait for the second prompt
        # simply wait 1 second here.
        # csr#>
        # csr#>
        sleep(1)
      else:
        return to_text(out, errors='surrogate_or_strict')

    index, match, out = tn.expect(prompts, command_timeout)
    if index < 0:
      tn.close()
      module.fail_json(msg='Failed to expect prompts: %s' % command)
    matched_prompt = match.group().strip()
    add_prompt_history(module, matched_prompt)
    add_raw_outputs(module, out)

    return to_text(out, errors='surrogate_or_strict')

  except EOFError as e:
    tn.close()
    module.fail_json(msg='Telnet action failed: %s' % to_text(e))


def run_commands(module):
  commands = module.params['commands']
  commands = to_list(commands)
  pause = module.params['pause']

  responses = list()
  for i, cmd in enumerate(commands):
    if isinstance(cmd, dict):
      command = cmd.get('command', '')
      prompt = cmd.get('prompt', None)
      answer = cmd.get('answer', None)
    else:
      command = cmd
      prompt = None
      answer = None

    out = send_and_wait(module, command, prompt=prompt, answer=answer)

    # remove command echo and tailing prompt
    lines = out.splitlines()
    if len(lines) >= 1:
      lines = lines[1:-1]
    out = '\n'.join(lines)

    responses.append(out)

    if i != len(commands) -1:
      sleep(pause)

  return responses
