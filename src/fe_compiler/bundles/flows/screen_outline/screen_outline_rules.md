# Screen outline — authoring rules

1. Every screen in `SCREENS.LIST` must carry a stable `SCR-NN`
   id. Ids are assigned sequentially from the entry point;
   reusing an id across screens is forbidden.
2. Section markers (`[SECTION_START:SCREENS.*]` /
   `[SECTION_END:SCREENS.*]`) must always come in matched pairs.
3. Required sections: `SCREENS.OVERVIEW`, `SCREENS.LIST`,
   `SCREENS.NAVIGATION`, `SCREENS.COMPONENT_SURFACE`.
4. Every `SCR-NN` referenced in `SCREENS.NAVIGATION` must also
   appear in `SCREENS.LIST`. Navigation cannot reference screens
   that do not exist.
5. `SCREENS.NAVIGATION` records edges using the
   `<SCR-NN → SCR-NN — trigger>` shape. The `trigger` is a short
   human-readable phrase (button label, event, route change).
6. Components in `SCREENS.COMPONENT_SURFACE` list the screens
   they appear on; a component that appears on only one screen
   must still declare that screen explicitly.
7. Placeholder text wrapped in `<...>` must be resolved before
   the artifact is considered final.
