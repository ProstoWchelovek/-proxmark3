local os = require("os")
local ac = require('ansicolors')
local utils = require('utils')
local getopt = require('getopt')
local dash = string.rep('--', 32)

author = '    Author: jareckib - created 01.02.2025'
version = '    version v1.01'
desc = [[
    A simple script for searching the password for T5577. The script creates a
    dictionary starting from the entered starting year to the entered ending year.
    There are two search methods - DDMMYYYY or YYYYMMDD. Checking the entire year
    takes about 1 minute and 50 seconds. Date from 1900 to 2100. The script may be
    useful if the password is, for example, a date of birth.
]]
usage = [[
  script run lf_t55xx_chk_date
]]
arguments = [[
  script run lf_t55xx_chk_date -h    : this help
]]

local DEBUG = true

local function dbg(args)
    if not DEBUG then return end
    if type(args) == 'table' then
        for _, v in ipairs(args) do
            dbg(v)
        end
    else
        print('###', args)
    end
end

local function help()
    print()
    print(ac.green..author)
    print(version)
    print(ac.yellow..desc)
    print(ac.cyan..'  Usage'..ac.reset)
    print(usage)
    print(ac.cyan..'  Arguments'..ac.reset)
    print(arguments)
end

local dir = os.getenv('HOME') .. '/proxmark3/client/dictionaries/'
local dictionary_path = dir .. 'T5577date.dic'

local days_in_month = {
    [1] = 31, [2] = 28, [3] = 31, [4] = 30, [5] = 31, [6] = 30,
    [7] = 31, [8] = 31, [9] = 30, [10] = 31, [11] = 30, [12] = 31
}

local function generate_dictionary(start_year, end_year, mode)
    local file = io.open(dictionary_path, "w")
    if not file then
        print(ac.yellow .. '  ERROR: ' .. ac.reset .. 'Cannot create T5577date.dic')
        return false
    end

    for year = start_year, end_year do
        for month = 1, 12 do
            local days_in_current_month = days_in_month[month]
            if month == 2 and ((year % 4 == 0 and year % 100 ~= 0) or (year % 400 == 0)) then
                days_in_current_month = 29
            end

            for day = 1, days_in_current_month do
                local month_str = string.format("%02d", month)
                local day_str = string.format("%02d", day)
                local year_str = tostring(year)
                local entry = (mode == "1") and (year_str .. month_str .. day_str) or (day_str .. month_str .. year_str)
