from run_page.generator import Generator
import json

def restore_streaks():
    generator = Generator("run_page/data.db")
    activities_list = generator.load()
    with open("src/static/activities.json", "w") as f:
        json.dump(activities_list, f)
    print(f"Regenerated {len(activities_list)} records with streaks")

if __name__ == "__main__":
    restore_streaks()
