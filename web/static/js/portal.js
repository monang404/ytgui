function initPortal() {
    const role = localStorage.getItem("ytgui_user_role");
    if (role) {
        store.userRole = role;
    }
    applyRoleUI();
}

function applyRoleUI() {
    if (store.userRole === "portal") {
        dom.portalScreen.classList.add("portal-active");
        dom.appContainer.classList.add("portal-active");
        document.body.classList.remove("client-mode");
        if(dom.queueList && dom.queueFooter && dom.tabQueue) dom.tabQueue.insertBefore(dom.queueList, dom.queueFooter);
        dom.logoutBtn.style.display = "none";
    } else if (store.userRole === "client") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.add("client-mode");
        switchTab("home");
        if(dom.queueList && dom.tabHome) dom.tabHome.appendChild(dom.queueList);
        dom.logoutBtn.style.display = "none";
    } else if (store.userRole === "admin") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.remove("client-mode");
        if(dom.queueList && dom.queueFooter && dom.tabQueue) dom.tabQueue.insertBefore(dom.queueList, dom.queueFooter);
        dom.logoutBtn.style.display = "inline-flex";
    }
    renderHeader();
}

function logout() {
    store.userRole = "portal";
    store.adminUsername = "";
    store.adminPassword = "";
    localStorage.removeItem("ytgui_user_role");
    localStorage.removeItem("ytgui_admin_username");
    localStorage.removeItem("ytgui_admin_password");
    localStorage.removeItem("ytgui_session_token");
    if (window.location.pathname !== "/admin") {
        window.location.href = "/admin";
    } else {
        dom.portalClientBtn.style.display = "none";
        applyRoleUI();
        if (window.ws) {
            window.ws.close();
        }
    }
}
