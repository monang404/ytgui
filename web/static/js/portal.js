function initPortal() {
    const role = window.safeStorage ? window.safeStorage.get("ytgui_user_role") : localStorage.getItem("ytgui_user_role");
    if (role && role !== "client") {
        store.userRole = role;
    } else {
        store.userRole = "portal";
    }
    applyRoleUI();
}
