from run_page.utils import make_activities_file

make_activities_file("run_page/data.db", "GPX_OUT", "src/static/activities.json")
print("Regenerated with streaks")
