local getopt = require('getopt')
local utils = require('utils')
local ac = require('ansicolors')
local os = require('os')
local dash = string.rep('--', 32)
local dir = os.getenv('HOME') .. '/.proxmark3/logs/'
local logfile = (io.popen('dir /a-d /o-d /tw /b/s "' .. dir .. '" 2>nul:'):read("*a"):match("%C+"))
local command = core.console
local pm3 = require('pm3')
p = pm3.pm3()
command('clear')
author = ' jareckib - 12.03.2025'
version = ' v1.06'
mod = ' 20.03.2025'
desc = [[

  This simple script stores 1, 2 or 3 different EM4102 on a single T5577.
  There is an option to enter the number engraved on the fob in decimal form.
  The script can therefore be useful if the original EM4102 doesn't work but
  has an engraved ID number. By entering such an ID as a single EM4102, we
  can create a working copy of our damaged fob.
  A tag T5577 created in this way works with the following USB readers:

  - ACM08Y
  - ACM26C
  - Sycreader R60D
  - Elatech Multitech TWN4
]]
usage = [[
  script run lf_t55xx_multiwriter
]]
arguments = [[
  script run lf_t55xx_multiwriter -h    : this help
]]

local function help()
    print()
    print(ac.yellow..'  Author:'..ac.reset..author)
    print(ac.yellow..'  Version:'..ac.reset..version)
    print(ac.yellow..'  Modification date:'..ac.reset..mod)
    print(desc)
    print(ac.cyan .. '  Usage' .. ac.reset)
    print(usage)
    print(ac.cyan .. '  Arguments' .. ac.reset)
    print(arguments)
end

local function sleep(n)
    os.execute("sleep " ..tonumber(n))
end

function wait(msec)
   local t = os.clock()
   repeat
   until os.clock() > t + msec * 1e-3
end

local function timer(n)
    while n > 0 do
        io.write(ac.cyan.."::::: "..ac.yellow.. tonumber(n) ..ac.yellow.." sec "..ac.cyan..":::::\r"..ac.reset)
        sleep(1)
        io.flush()
        n = n-1
    end
end

local function reset_log_file()
    local file = io.open(logfile, "w+")
