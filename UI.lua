-- This file creates and manages the addon's UI panel with a stable, two-pane design.

local selectedGroup = nil -- Keep track of which group is being displayed
local itemCheckboxPool = {} -- A pool of reusable checkboxes for the item list

-- This function updates the item list on the right side of the panel.
local function UpdateItemList()
    if not selectedGroup or not MinEgenAddon_Groups then return end
    
    -- Find the group data from Groups.lua
    local groupData
    for _, g in ipairs(MinEgenAddon_Groups) do
        if g.name == selectedGroup then groupData = g; break; end
    end
    if not groupData then return end
    
    -- To ensure a consistent order, we sort the item IDs
    local sortedItemIDs = {}
    for itemID, _ in pairs(groupData.items) do table.insert(sortedItemIDs, itemID) end
    table.sort(sortedItemIDs)
    
    -- Hide all pooled checkboxes before showing the ones we need
    for _, checkbox in ipairs(itemCheckboxPool) do
        checkbox:Hide()
    end
    
    -- Configure and show a checkbox for each item
    local yOffset = 0
    for i, itemID in ipairs(sortedItemIDs) do
        if i > #itemCheckboxPool then break end -- Safety break if we have more items than pooled checkboxes

        local checkbox = itemCheckboxPool[i]
        local itemName = groupData.items[itemID]
        local groupSettings = MinEgenAddon_Settings.groups[selectedGroup]
        
        checkbox:ClearAllPoints()
        checkbox:SetPoint("TOPLEFT", 10, yOffset)
        
        _G[checkbox:GetName().."Text"]:SetText(itemName or "Item " .. itemID)
        checkbox:SetChecked(groupSettings.items[itemID])
        
        checkbox:SetScript("OnClick", function(self)
            MinEgenAddon_ToggleItem(selectedGroup, itemID, self:GetChecked())
        end)
        
        checkbox:Show()
        yOffset = yOffset - 30
    end
    
    -- Update the scrollable area's height
    local scrollChild = itemCheckboxPool[1]:GetParent()
    scrollChild:SetHeight(math.abs(yOffset) + 10)
end

function MinEgenAddon_CreateUI()
    local frame = CreateFrame("Frame", "MinEgenAddonFrame", UIParent)
    frame:SetBackdrop({
        bgFile = "Interface/DialogFrame/UI-DialogBox-Background",
        edgeFile = "Interface/DialogFrame/UI-DialogBox-Border",
        tile = true, tileSize = 32, edgeSize = 32,
        insets = { left = 11, right = 12, top = 12, bottom = 11 }
    })
    frame:SetSize(500, 420)
    frame:SetPoint("CENTER")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame:Hide()

    local title = frame:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    title:SetPoint("TOP", 0, -20)
    title:SetText("MinEgenAddon Group Settings")

    local closeButton = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    closeButton:SetPoint("TOPRIGHT", -5, -5)

    -- --- Left Pane: Group List ---
    local yOffset = -60
    if MinEgenAddon_Groups and MinEgenAddon_Settings then
        for i, group in ipairs(MinEgenAddon_Groups) do
            local groupButton = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
            groupButton:SetPoint("TOPLEFT", 20, yOffset)
            groupButton:SetSize(140, 25)
            groupButton:SetText(group.name)
            
            groupButton:SetScript("OnClick", function()
                selectedGroup = group.name
                UpdateItemList()
            end)
            yOffset = yOffset - 35
        end
    end
    
    -- --- Right Pane: Item List Container ---
    local itemContainer = CreateFrame("Frame", nil, frame)
    itemContainer:SetPoint("TOPLEFT", 170, -50)
    itemContainer:SetPoint("BOTTOMRIGHT", -15, 15)
    itemContainer:SetBackdrop({bgFile = "Interface/Tooltips/UI-Tooltip-Background", edgeFile = "Interface/Tooltips/UI-Tooltip-Border", tile = true, tileSize = 16, edgeSize = 16, insets = { left = 4, right = 4, top = 4, bottom = 4 }});
    itemContainer:SetBackdropColor(0,0,0,0.5);

    -- "Enable All" Button
    local enableAllButton = CreateFrame("Button", nil, itemContainer, "UIPanelButtonTemplate")
    enableAllButton:SetPoint("TOPLEFT", 10, -10)
    enableAllButton:SetSize(120, 22)
    enableAllButton:SetText("Enable All")
    enableAllButton:SetScript("OnClick", function()
        if not selectedGroup then return end
        for itemID, _ in pairs(MinEgenAddon_Settings.groups[selectedGroup].items) do
            MinEgenAddon_Settings.groups[selectedGroup].items[itemID] = true
        end
        MinEgenAddon_RebuildMap()
        UpdateItemList() -- Refresh the view
    end)

    -- "Disable All" Button
    local disableAllButton = CreateFrame("Button", nil, itemContainer, "UIPanelButtonTemplate")
    disableAllButton:SetPoint("LEFT", enableAllButton, "RIGHT", 10, 0)
    disableAllButton:SetSize(120, 22)
    disableAllButton:SetText("Disable All")
    disableAllButton:SetScript("OnClick", function()
        if not selectedGroup then return end
        for itemID, _ in pairs(MinEgenAddon_Settings.groups[selectedGroup].items) do
            MinEgenAddon_Settings.groups[selectedGroup].items[itemID] = false
        end
        MinEgenAddon_RebuildMap()
        UpdateItemList() -- Refresh the view
    end)
    
    -- Scroll Frame for items
    local scrollFrame = CreateFrame("ScrollFrame", nil, itemContainer, "UIPanelScrollFrameTemplate")
    scrollFrame:SetPoint("TOPLEFT", 5, -40)
    scrollFrame:SetPoint("BOTTOMRIGHT", -25, 5)
    
    local scrollChild = CreateFrame("Frame")
    scrollChild:SetSize(250, 1)
    scrollFrame:SetScrollChild(scrollChild)
    
    -- Create the checkbox pool
    for i=1, 50 do -- Create a pool of 50 checkboxes, which should be enough for most groups
        local checkbox = CreateFrame("CheckButton", "MinEgenAddonPoolCheck"..i, scrollChild, "UICheckButtonTemplate")
        checkbox:Hide()
        table.insert(itemCheckboxPool, checkbox)
    end
end
