-- This file adds a custom panel to the Auction House for group shopping.

local searchQueue = {}
local queueIndex = 1
local isSearching = false

local function ProcessSearchQueue()
    if not searchQueue[queueIndex] then
        isSearching = false
        print("MinEgenAddon: Group search complete!")
        PanelTemplates_SetTab(AuctionFrame, 1)
        AuctionFrameBrowse_Update()
        return
    end
    
    local itemName = searchQueue[queueIndex]
    print("MinEgenAddon: Searching for '" .. itemName .. "' (" .. queueIndex .. "/" .. #searchQueue .. ")")
    
    BrowseName:SetText(itemName)
    QueryAuctionItems(itemName, nil, nil, nil, nil, nil, nil, nil, nil)
end

function MinEgenAddon_CreateAHPanel()
    if MinEgenAddon_AHPanelInitialized then return end

    local frame = CreateFrame("Frame", "MinEgenAddonAHPanel", AuctionFrame)
    frame:SetAllPoints(AuctionFrame)
    frame:SetFrameStrata("HIGH") -- **THE FIX: This forces the panel to draw on top.**
    frame:Hide()

    local tab = CreateFrame("Button", "MinEgenAddonAHTab", AuctionFrame, "AuctionTabTemplate")
    tab:SetText("Shopping")
    tab:SetPoint("LEFT", AuctionFrameTab3, "RIGHT", -15, 0)
    
    local dropdown = CreateFrame("Frame", "MinEgenAddonGroupDropdown", frame, "UIDropDownMenuTemplate")
    dropdown:SetPoint("TOPLEFT", 20, -80)
    
    local searchButton = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    searchButton:SetPoint("LEFT", dropdown, "RIGHT", 10, 0)
    searchButton:SetText("Search Group")
    searchButton:SetSize(120, 25)
    
    local dropdownInitialized = false
    local function InitializeDropdown()
        if dropdownInitialized then return end

        local info = {}
        if MinEgenAddon_Groups and MinEgenAddon_Settings then
            for _, group in ipairs(MinEgenAddon_Groups) do
                if MinEgenAddon_Settings.groups[group.name] and MinEgenAddon_Settings.groups[group.name].enabled then
                    table.insert(info, { text = group.name, func = function() UIDropDownMenu_SetText(dropdown, group.name) end })
                end
            end
        end
        UIDropDownMenu_Initialize(dropdown, info)
        UIDropDownMenu_SetText(dropdown, "Select a Group")
        dropdownInitialized = true
    end
    
    tab:SetScript("OnClick", function()
        PanelTemplates_SetTab(AuctionFrame, 4)
        AuctionFrameBrowse:Hide()
        AuctionFrameBid:Hide()
        AuctionFrameAuction:Hide()
        InitializeDropdown()
        frame:Show()
    end)
    
    local function HideCustomPanel()
        if frame:IsShown() then frame:Hide() end
    end
    AuctionFrameTab1:HookScript("OnClick", HideCustomPanel)
    AuctionFrameTab2:HookScript("OnClick", HideCustomPanel)
    AuctionFrameTab3:HookScript("OnClick", HideCustomPanel)

    searchButton:SetScript("OnClick", function()
        if isSearching then return end
        local selectedGroupName = UIDropDownMenu_GetText(dropdown)
        if not selectedGroupName or selectedGroupName == "Select a Group" then
            print("MinEgenAddon: Please select a group to search.")
            return
        end

        wipe(searchQueue)
        local groupData
        for _, g in ipairs(MinEgenAddon_Groups) do
            if g.name == selectedGroupName then groupData = g; break; end
        end
        if not groupData then return end
        
        local groupSettings = MinEgenAddon_Settings.groups[selectedGroupName].items
        for itemID, itemName in pairs(groupData.items) do
            if groupSettings[itemID] then table.insert(searchQueue, itemName) end
        end

        if #searchQueue == 0 then
            print("MinEgenAddon: No items enabled in the selected group.")
            return
        end

        isSearching = true
        queueIndex = 1
        ProcessSearchQueue()
    end)
    
    local searchEventFrame = CreateFrame("Frame")
    searchEventFrame:RegisterEvent("AUCTION_ITEM_LIST_UPDATE")
    searchEventFrame:SetScript("OnEvent", function(self, event, ...)
        if isSearching then
            queueIndex = queueIndex + 1
            ProcessSearchQueue()
        end
    end)
    
    MinEgenAddon_AHPanelInitialized = true
    print("MinEgenAddon: Shopping panel created successfully.")
end
