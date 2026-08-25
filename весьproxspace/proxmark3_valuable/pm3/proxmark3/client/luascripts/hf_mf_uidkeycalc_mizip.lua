local bin = require('bin')
local getopt = require('getopt')
local lib14a = require('read14a')
local utils =  require('utils')
local ansicolors  = require('ansicolors')

copyright = ''
author = 'Iceman'
version = 'v1.0.2'
desc = [[
This script calculates mifare keys based on uid diversification for mizip.
Algo not found by me.
]]
example = [[
     -- if called without, it reads tag uid
     script run hf_mf_uidkeycalc-mizip

     --
     script run hf_mf_uidkeycalc-mizip -u 11223344
]]
usage = [[
script run hf_mf_uidkeycalc-mizip -h -u <uid>
]]
arguments = [[
    -h             : this help
    -u <UID>       : UID
]]
local DEBUG = true
local bxor = bit32.bxor
local _xortable = {
    --[[ sector key A/B, 6byte xor
    --]]
    {1, '09125a2589e5', 'F12C8453D821'},
    {2, 'AB75C937922F', '73E799FE3241'},
    {3, 'E27241AF2C09', 'AA4D137656AE'},
    {4, '317AB72F4490', 'B01327272DFD'},
}
---
-- A debug printout-function
local function dbg(args)
    if not DEBUG then return end
    if type(args) == 'table' then
        local i = 1
        while args[i] do
            dbg(args[i])
            i = i+1
        end
    else
        print('###', args)
    end
end
---
-- This is only meant to be used when errors occur
local function oops(err)
    print('ERROR: ', err)
    core.clearCommandBuffer()
    return nil, err
end
---
-- Usage help
local function help()
    print(copyright)
    print(author)
    print(version)
    print(desc)
    print(ansicolors.cyan..'Usage'..ansicolors.reset)
    print(usage)
    print(ansicolors.cyan..'Arguments'..ansicolors.reset)
    print(arguments)
    print(ansicolors.cyan..'Example usage'..ansicolors.reset)
    print(example)
end
--
-- Exit message
local function exitMsg(msg)
    print( string.rep('--',20) )
    print( string.rep('--',20) )
    print(msg)
    print()
end
--
-- dumps all keys to file
local function dumptofile(uid, keys)
    dbg('dumping keys to file')

    if utils.confirm('Do you wish to save the keys to dumpfile?') then
        local filename = ('hf-mf-%s-key.bin'):format(uid);
        local destination = utils.input('Select a filename to store to', filename)
        local file = io.open(destination, 'wb')
        if file == nil then
            print('Could not write to file ', destination)
            return
        end

        -- Mifare Mini has 5 sectors,
        local key_a = ''
        local key_b = ''

        for sector = 0, #keys do
            local keyA, keyB = table.unpack(keys[sector])
            key_a = key_a .. bin.pack('H', keyA);
            key_b = key_b .. bin.pack('H', keyB);
        end
