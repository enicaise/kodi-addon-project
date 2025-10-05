# main.py

import xbmc
import xbmcgui
import xbmcaddon

# Initialisation de l'addon
addon_id = 'script.program.mysqlassistant'  
addon = xbmcaddon.Addon(id=addon_id)

def main():
    xbmcgui.Dialog().ok(addon.getAddonInfo('name'), addon.getLocalizedString(30000))  # Affiche un message de bienvenue

if __name__ == '__main__':
    main()