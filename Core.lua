local addonName, addonTable = ...

MinEgenAddon_Settings = nil
MinEgenAddon_AHPanelInitialized = false
local itemToGroupMap = {}
local isInitialized = false
local isAHHooked = false

function MinEgenAddon_RebuildMap()
    wipe(itemToGroupMap)
    if not MinEgenAddon_Groups or not MinEgenAddon_Settings then return end
    for _, group in ipairs(MinEgenAddon_Groups) do
        local groupSettings = MinEgenAddon_Settings.groups[group.name]
        if groupSettings and groupSettings.enabled then
            for itemID, _ in pairs(group.items) do
                if groupSettings.items[itemID] then itemToGroupMap[itemID] = group.name end
            end
        end
    end
end

function MinEgenAddon_ToggleItem(groupName, itemID, isEnabled)
    if MinEgenAddon_Settings and MinEgenAddon_Settings.groups[groupName] then
        MinEgenAddon_Settings.groups[groupName].items[itemID] = isEnabled
        MinEgenAddon_RebuildMap()
    end
end

function MinEgenAddon_ToggleGroup(groupName, isEnabled)
    if MinEgenAddon_Settings and MinEgenAddon_Settings.groups[groupName] then
        MinEgenAddon_Settings.groups[groupName].enabled = isEnabled
        MinEgenAddon_RebuildMap()
    end
end

local function SecurelyInitializeAHPanel()
    if MinEgenAddon_AHPanelInitialized then return end
    local success, err = pcall(MinEgenAddon_CreateAHPanel)
    if not success then print("|cffff0000MinEgenAddon AH Hook ERROR: " .. tostring(err) .. "|r") end
end

local function InitializeAddon()
    if isInitialized then return end

    if not MinEgenAddon_Settings then MinEgenAddon_Settings = { groups = {} } end
    if MinEgenAddon_Groups then
        for _, group in ipairs(MinEgenAddon_Groups) do
            if not MinEgenAddon_Settings.groups[group.name] then
                MinEgenAddon_Settings.groups[group.name] = { enabled = true, items = {} }
            end
            for itemID, _ in pairs(group.items) do
                if MinEgenAddon_Settings.groups[group.name].items[itemID] == nil then
                    MinEgenAddon_Settings.groups[group.name].items[itemID] = true
                end
            end
        end
    end

    MinEgenAddon_CreateUI()
    MinEgenAddon_RebuildMap()
    
    SLASH_MINEGENADDON1 = "/mea"
    SlashCmdList["MINEGENADDON"] = function() MinEgenAddonFrame:SetShown(not MinEgenAddonFrame:IsShown()) end

    print("MinEgenAddon: Successfully Initialized.")
    isInitialized = true
end

-- **THE DEFINITIVE FIX: Use the reliable ADDON_LOADED event**
local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:SetScript("OnEvent", function(self, event, arg1)
    -- Initialize our addon when it loads
    if arg1 == addonName then
        pcall(InitializeAddon)
    -- Wait for the Blizzard AH to load, then safely hook into it
    elseif arg1 == "Blizzard_AuctionUI" and not isAHHooked then
        hooksecurefunc("AuctionFrame_Show", SecurelyInitializeAHPanel)
        print("MinEgenAddon: Successfully hooked into the Auction House.")
        isAHHooked = true
        -- We can stop listening now
        self:UnregisterEvent("ADDON_LOADED")
    end
end)


-- === Tooltip Functionality === (No changes below this line)
local GOLD_ICON = "|TInterface\\MoneyFrame\\UI-GoldIcon:0|t"
local SILVER_ICON = "|TInterface\\MoneyFrame\\UI-SilverIcon:0|t"
local COPPER_ICON = "|TInterface\\MoneyFrame\\UI-CopperIcon:0|t"

local function FormatPrice(price)
    if not price or price <= 0 then return "" end
    local gold = floor(price / 10000)
    local silver = floor((price % 10000) / 100)
    local copper = price % 100
    local result = ""
    if gold > 0 then result = result .. gold .. GOLD_ICON .. " " end
    if silver > 0 then result = result .. silver .. SILVER_ICON .. " " end
    if copper > 0 or (gold == 0 and silver == 0) then result = result .. copper .. COPPER_ICON end
    return result:gsub(" $", "")
end

GameTooltip:HookScript("OnTooltipSetItem", function(tooltip)
    local name, link = tooltip:GetItem()
    if not link then return end
    
    local itemID = tonumber(link:match("item:(%d+)"))
    if not itemID then return end
    
    local groupName = itemToGroupMap[itemID]
    local price = MinEgenAddon_Prices and MinEgenAddon_Prices[itemID]
    
    if groupName or price then tooltip:AddLine(" ") end
    if groupName then tooltip:AddLine("Group: " .. groupName, 0.5, 1.0, 0.5) end

    if price then
        local formattedPrice = FormatPrice(price)
        if formattedPrice and #formattedPrice > 0 then
            tooltip:AddLine("Min Buyout: " .. formattedPrice, 1, 0.84, 0)
        end
    end

    if groupName or price then tooltip:Show() end
end)
