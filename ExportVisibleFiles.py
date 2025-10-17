#Author-Linus
#Description-Export all visible components and bodies to separate files

import adsk.core, adsk.fusion, adsk.cam, traceback, os

# Global variables
app = adsk.core.Application.get()
ui = app.userInterface

# Command info
CMD_ID = 'ExportVisibleFiles'
CMD_NAME = 'Export Visible Files'
CMD_TOOLTIP = 'Export all visible components and bodies to separate files'
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
ICON_FOLDER = './resources/'

# Keep event handlers referenced
handlers = []

# --- Helper functions ---
def get_visible_entities(root_comp, export_components, export_bodies):
    """Return a list of visible components and/or bodies"""
    visible_items = []
    if export_components:
        for comp in root_comp.allComponents:
            if comp.isVisible:
                visible_items.append(comp)
    if export_bodies:
        for comp in root_comp.allComponents:
            for body in comp.bRepBodies:
                if body.isVisible:
                    visible_items.append(body)
    return visible_items

def sanitize_filename(name):
    """Remove illegal filename characters"""
    return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

def get_file_extension(format_str):
    return {
        'STEP': 'step',
        'STL': 'stl',
        'IGES': 'igs',
        'SAT': 'sat'
    }.get(format_str, 'stp')

def export_entity(entity, folder, export_format):
    exportMgr = app.activeProduct.exportManager
    filename = sanitize_filename(entity.name) + '.' + get_file_extension(export_format)
    filepath = os.path.join(folder, filename)
    if isinstance(entity, adsk.fusion.Component):
        if export_format == 'STEP':
            options = exportMgr.createSTEPExportOptions(filepath, entity)
        elif export_format == 'IGES':
            options = exportMgr.createIGESExportOptions(filepath, entity)
        elif export_format == 'SAT':
            options = exportMgr.createSATExportOptions(filepath, entity)
        elif export_format == 'STL':
            options = exportMgr.createSTLExportOptions(entity.bRepBodies, filepath)
        else:
            ui.messageBox(f'Unsupported format: {export_format}')
            return
    elif isinstance(entity, adsk.fusion.BRepBody):
        if export_format == 'STL':
            options = exportMgr.createSTLExportOptions([entity], filepath)
        else:
            ui.messageBox(f'Bodies can only be exported as STL')
            return
    exportMgr.execute(options)

# --- Event handlers ---
class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # Checkboxes
            inputs.addBoolValueInput('exportComponents', 'Export Components', True)
            inputs.addBoolValueInput('exportBodies', 'Export Bodies', True)

            # Format dropdown
            format_dropdown = inputs.addDropDownCommandInput('fileFormat', 'File Format', adsk.core.DropDownStyles.TextListDropDownStyle)
            for f in ['STEP', 'STL', 'IGES', 'SAT']:
                format_dropdown.listItems.add(f, f=='STEP')

            # Read-only counter
            inputs.addTextBoxCommandInput('fileCount', 'Files to Export', '0', 1, True)

            # Add handlers
            onInputChanged = InputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            handlers.append(onInputChanged)

            onExecute = CommandExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

        except:
            ui.messageBox('Failed in CommandCreatedHandler:\n{}'.format(traceback.format_exc()))

class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmdInputs = args.inputs
            design = app.activeProduct
            root = design.rootComponent
            export_components = cmdInputs.itemById('exportComponents').value
            export_bodies = cmdInputs.itemById('exportBodies').value
            count_box = cmdInputs.itemById('fileCount')
            visible_items = get_visible_entities(root, export_components, export_bodies)
            count_box.text = str(len(visible_items))
        except:
            ui.messageBox('Failed in InputChangedHandler:\n{}'.format(traceback.format_exc()))

class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            design = app.activeProduct
            root = design.rootComponent
            cmdInputs = args.firingEvent.sender.commandInputs

            export_components = cmdInputs.itemById('exportComponents').value
            export_bodies = cmdInputs.itemById('exportBodies').value
            export_format = cmdInputs.itemById('fileFormat').selectedItem.name

            visible_items = get_visible_entities(root, export_components, export_bodies)
            folder = ui.selectFolderDialog('Select folder for exported files')
            if not folder:
                return

            progress = ui.createProgressDialog()
            progress.isBackgroundTranslucent = False
            progress.show('Exporting files', 'Exporting...', 0, len(visible_items), 1)

            for i, item in enumerate(visible_items):
                export_entity(item, folder, export_format)
                progress.progressValue = i + 1

            progress.hide()
            ui.messageBox(f'Exported {len(visible_items)} files successfully.')

        except:
            ui.messageBox('Failed in CommandExecuteHandler:\n{}'.format(traceback.format_exc()))

# --- Startup / Shutdown ---
def run(context):
    try:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        cmdDef = ui.commandDefinitions.itemById(CMD_ID)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_TOOLTIP, ICON_FOLDER)

        onCreated = CommandCreatedHandler()
        cmdDef.commandCreated.add(onCreated)
        handlers.append(onCreated)

        panel.controls.addCommand(cmdDef)
    except:
        ui.messageBox('Add-in startup failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    try:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        ctrl = panel.controls.itemById(CMD_ID)
        if ctrl:
            ctrl.deleteMe()
        cmdDef = ui.commandDefinitions.itemById(CMD_ID)
        if cmdDef:
            cmdDef.deleteMe()
    except:
        ui.messageBox('Add-in shutdown failed:\n{}'.format(traceback.format_exc()))
