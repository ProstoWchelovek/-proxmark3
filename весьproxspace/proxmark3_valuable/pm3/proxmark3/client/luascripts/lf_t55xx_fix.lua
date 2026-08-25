local getopt = require('getopt')
local utils = require('utils')
local ac = require('ansicolors')
local os = require('os')
local dash = string.rep('--', 32)
local dir = os.getenv('HOME') .. '/.proxmark3/logs/'
local logfile = (io.popen('dir /a-d /o-d /tw /b/s "' .. dir .. '" 2>nul:'):read("*a"):match("%C+"))
local pm3 = require('pm3')
p = pm3.pm3()
local command = core.console
command('clear')

author = '  Author: jareckib - 15.02.2025'
version = '  version v1.02'
desc = [[
  This simple script first checks if a password has been set for the T5577.
  It uses the dictionary t55xx_default_pwds.dic for this purpose. If a password
  is found, it uses the wipe command to erase the T5577. Then the reanimation
  procedure is applied. If the password is not found or doesn't exist the script
  only performs the reanimation procedure. The script revives 99% of blocked tags.
 ]]
usage = [[
  script run lf_t55xx_fix
]]
arguments = [[
  script run lf_t55xx_fix -h    : this help
]]

local function help()
    print()
    print(author)
    print(version)
    print(desc)
    print(ac.cyan..'  Usage'..ac.reset)
    print(usage)
    print(ac.cyan..'  Arguments'..ac.reset)
    print(arguments)
end

local function read_log_file(logfile)
    local file = io.open(logfile, "r")
    if not file then
        return nil
    end
    local content = file:read("*all")
