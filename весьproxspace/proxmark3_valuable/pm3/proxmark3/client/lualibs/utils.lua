--[[
    This may be moved to a separate library at some point (Holiman)
--]]
local Utils =
{
    -- Asks the user for Yes or No
    confirm = function(message, ...)
        local answer
        message = message .. " [y/n] ?"
        repeat
            io.write(message)
            io.flush()
            answer = io.read()
            if answer == 'Y' or answer == "y" then
                return true
            elseif answer == 'N' or answer == 'n' then
                return false
            end
        until false
    end,
    ---
    -- Asks the user for input
    input = function (message, default)
        local answer = ''
        if default ~= nil then
            message = message .. " (default: ".. default.. " )"
        end
        io.write(message, "\n > ")
        io.flush()
        answer = io.read("*L")
        answer = string.gsub(answer, "\r\n", "")
        answer = string.gsub(answer, "\n", "")
        if answer == '' or answer == nil then answer = default end
        return answer
    end,

    ------------ FILE READING
    ReadDumpFile = function (filename)

        filename = filename or 'dumpdata.bin'
        if #filename == 0 then
            return nil, 'Filename length is zero'
        end

        infile = io.open(filename, "rb")
        if infile == nil then
            return nil, string.format("Could not read file %s",filename)
        end
        local t = infile:read("*all")
        io.close(infile)
        len = string.len(t)
        local  _,hex = bin.unpack(("H%d"):format(len),t)
        return hex
    end,

    ------------ FILE WRITING (EML)
    --- Writes an eml-file.
    -- @param uid - the uid of the tag. Used in filename
    -- @param blockData. Assumed to be on the format {'\0\1\2\3,'\b\e\e\f' ...,
    -- that is, blockData[row] contains a string with the actual data, not ascii hex representation
    -- return filename if all went well,
    -- @reurn nil, error message if unsuccessful
    WriteDumpFile = function(uid, blockData)
        local destination = string.format("%s.eml", uid)
        local file = io.open(destination, "w")
        if file == nil then
            return nil, string.format("Could not write to file %s", destination)
        end
        local rowlen = string.len(blockData[1])

        for i,block in ipairs(blockData) do
            if rowlen ~= string.len(block) then
                prlog(string.format("WARNING: Dumpdata seems corrupted, line %d was not the same length as line 1",i))
            end

            local formatString = string.format("H%d", string.len(block))
            local _,hex = bin.unpack(formatString,block)
