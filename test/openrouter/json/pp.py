# --- START OF migrate_history.py ---
import os
import json

# --- Configuration ---
# The name of your old, single history file.
OLD_HISTORY_FILE = "chat_histories.json"

# The name of the new folder where the individual history files will be created.
NEW_HISTORY_FOLDER = "chat_histories"


def migrate_histories():
    """
    Reads the old single-file history and converts it into a new
    folder-based structure where each conversation is a separate file.
    """
    print("--- Chat History Migration Tool ---")

    # 1. Check if the old history file exists
    if not os.path.exists(OLD_HISTORY_FILE):
        print(f"🔴 ERROR: The old history file '{OLD_HISTORY_FILE}' was not found in this directory.")
        print("   Please place this script next to your old history file and run it again.")
        return

    # 2. Create the new destination folder
    try:
        os.makedirs(NEW_HISTORY_FOLDER, exist_ok=True)
        print(f"✅ Destination folder '{NEW_HISTORY_FOLDER}' is ready.")
    except Exception as e:
        print(f"🔴 ERROR: Could not create the destination folder. Reason: {e}")
        return

    # 3. Load the entire old history data
    try:
        with open(OLD_HISTORY_FILE, 'r') as f:
            all_histories = json.load(f)
        if not isinstance(all_histories, dict):
            print("🔴 ERROR: The old history file is not in the expected format (a dictionary).")
            return
        print(f"✅ Successfully loaded data from '{OLD_HISTORY_FILE}'. Found {len(all_histories)} conversation(s).")
    except Exception as e:
        print(f"🔴 ERROR: Could not read or parse the old history file. Reason: {e}")
        return

    # 4. Iterate and create a new file for each conversation
    successful_migrations = 0
    for context_id, history_list in all_histories.items():
        try:
            # The new filename is just the context ID (channel/user ID)
            new_filepath = os.path.join(NEW_HISTORY_FOLDER, f"{context_id}.json")
            
            with open(new_filepath, 'w') as f:
                json.dump(history_list, f, indent=4)
                
            print(f"   -> Migrated history for context ID: {context_id}")
            successful_migrations += 1
        except Exception as e:
            print(f"   -> ⚠️ FAILED to migrate history for context ID: {context_id}. Reason: {e}")

    print("\n--- Migration Complete ---")
    print(f"✅ Successfully converted {successful_migrations} out of {len(all_histories)} histories.")
    print(f"Your new history files are located in the '{NEW_HISTORY_FOLDER}' folder.")
    print("You can now safely delete the old '{OLD_HISTORY_FILE}' file if you wish.")


# This makes the script runnable
if __name__ == "__main__":
    migrate_histories()

# --- END OF migrate_history.py ---