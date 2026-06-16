import asyncio
from tui.dashboard import Dashboard
from core.state import AppState

async def test_layout():
    # Initialize the app with dummy state
    app = Dashboard(AppState())
    
    # Run the app in test mode (headless, 40 cols x 30 rows)
    async with app.run_test(size=(40, 30)) as pilot:
        # Give the app a moment to layout
        await asyncio.sleep(0.1)
        
        main_grid = app.query_one("#main_grid")
        side_panel = app.query_one("#side_panel")
        
        print("--- Layout Check ---")
        print(f"Screen size: {app.screen.size}")
        print(f"#main_grid size: {main_grid.size}")
        print(f"#side_panel size: {side_panel.size}")
        print("--------------------")
        
        if main_grid.size.height > 0 and side_panel.size.height > 0:
            print("SUCCESS: Both #main_grid and #side_panel have positive height.")
        else:
            print("ERROR: Collapse detected! One of the containers has height 0.")

if __name__ == "__main__":
    asyncio.run(test_layout())
