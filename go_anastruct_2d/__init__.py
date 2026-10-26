"""GO 2D Structural — anaStruct extension entry point for IngeTrazo Plugin API v2."""
from .constants import VERSION


def setup(app):
    from .constants import PLUGIN_NAME, SUPPORTED_INGETRAZO_API
    if getattr(app, "api_version", 0) != SUPPORTED_INGETRAZO_API:
        raise RuntimeError("GO 2D Structural — anaStruct requires IngeTrazo Plugin API v2")
    existing = getattr(app.window, "_go_anastruct_2d_panel", None)
    if existing is not None:
        return existing
    from .ui import Panel
    panel = Panel(app)
    dock = app.add_panel("GO 2D anaStruct", panel)
    app.add_overlay(panel.overlay.paint)
    app.add_pickable(pick=panel.pick, on_select=panel.selected, delete=panel.delete_item)
    app.add_snap_provider(panel.snap_internal)
    app.on_document_changed(panel.refresh)
    action = app.add_menu_action(
        f"{PLUGIN_NAME} v{VERSION}",
        lambda: app.show_panel(dock),
        tip="2D beam, frame and truss analysis using anaStruct",
    )
    submenu = app.add_menu("GO 2D Structural — anaStruct")
    if submenu is not None:
        show = submenu.addAction("Show panel")
        show.triggered.connect(lambda _checked=False: app.show_panel(dock))
        examples_menu = submenu.addMenu("Load example")
        from .examples import EXAMPLES
        for label in EXAMPLES:
            item = examples_menu.addAction(label)
            item.triggered.connect(lambda _checked=False, name=label: panel.load_example(name))
    panel.dock = dock
    panel.menu_action = action
    app.window._go_anastruct_2d_panel = panel
    # Keep optional toolbar registration from breaking the core extension.
    try:
        from .toolbar import register_toolbar
        panel.toolbar = register_toolbar(app, panel, dock)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "GO anaStruct toolbar could not be registered"
        )
    return panel


__version__ = VERSION
