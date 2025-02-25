"""Generate economic scenarios from Ca-MK-Ox Arc dwellings, employment, GVA data
"""
import pandas as pd


def main():
  update_baseline_for_simim()

  scenario_names = [
    "0-unplanned",
    "1-new-cities",
    "2-expansion",
    "3-new-cities23",
    "4-expansion23",
    "5-new-cities23-nb",
    "6-new-cities30-nb",
  ]
  arclads = pd.read_csv("data/scenarios/camkox_lads.csv").geo_code.unique()
  baseline = read_data("baseline", arclads)

  for scenario_name in scenario_names:
    # read scenario data
    scenario = read_data(scenario_name, arclads)

    # calculate diff from baseline, rounded as int
    scenario = scenario.join(baseline, lsuffix="_scen", rsuffix="_base")
    scenario["GVA"] = (scenario.gva_scen - scenario.gva_base)
    scenario["JOBS"] = (scenario.employment_scen - scenario.employment_base)
    scenario["HOUSEHOLDS"] = (scenario.dwellings_scen - scenario.dwellings_base)
    scenario = scenario[
      ["GVA", "JOBS", "HOUSEHOLDS"]
    ].reset_index().rename({"lad_uk_2016": "GEOGRAPHY_CODE", "timestep": "YEAR"}, axis=1)

    # Calculate year-on-year differences
    years = list(reversed(sorted(scenario.YEAR.unique())))

    df = scenario.pivot(index="GEOGRAPHY_CODE", columns="YEAR", values=["GVA", "JOBS", "HOUSEHOLDS"])
    for key in ["GVA", "JOBS", "HOUSEHOLDS"]:
      dfk = df[key].copy()
      for i, year in enumerate(years):
        if year == scenario.YEAR.min():
          dfk[year] = 0
        else:
          dfk[year] = dfk[year] - dfk[years[i + 1]]
      df[key] = dfk

    unpivot = df[["GVA"]].reset_index() \
        .melt(id_vars="GEOGRAPHY_CODE") \
        [["GEOGRAPHY_CODE", "YEAR"]]

    for key in ["GVA", "JOBS", "HOUSEHOLDS"]:
      col = df[[key]].reset_index() \
        .melt(id_vars="GEOGRAPHY_CODE") \
        [["GEOGRAPHY_CODE", "YEAR", "value"]] \
        .rename(columns={"value": key})
      unpivot = unpivot.merge(col, on=["GEOGRAPHY_CODE", "YEAR"])

    scenario = unpivot
    # # magic scaling factor to manipulate model
    # scenario["GVA"] *= 10
    # scenario["JOBS"] *= 10
    # scenario["HOUSEHOLDS"] *= 5

    scenario["GVA"] = scenario["GVA"].round(6)
    scenario["JOBS"] = (scenario["JOBS"] * 1000).round().astype(int)  # convert from 1000s jobs to jobs
    scenario["HOUSEHOLDS"] = scenario["HOUSEHOLDS"].round().astype(int)

    # Filter to include only 2019 and later
    scenario = scenario[scenario.YEAR >= 2019]

    # output households-only scenario
    scenario[["YEAR", "GEOGRAPHY_CODE", "HOUSEHOLDS"]].to_csv(
      "data/scenarios/scenario{}__h.csv".format(scenario_name), index=False)

    # output households-gva-jobs scenarios
    scenario.to_csv("data/scenarios/scenario{}__gjh.csv".format(scenario_name), index=False)


def read_data(key, arclads):
  """Read csvs and merge to single dataframe
  """
  # HACK hard-code match for economics scenarios against 23k dwellings scenarios
  if "new-cities" in key:
    econ_key = "1-new-cities"
  elif key == "4-expansion23":
    econ_key = "2-expansion"
  else:
    econ_key = key

  df_gva = pd.read_csv("data/arc/arc_gva__{}.csv".format(econ_key))
  df_emp = pd.read_csv("data/arc/arc_employment__{}.csv".format(econ_key))
  df_dwl = pd.read_csv("data/arc/arc_dwellings__{}.csv".format(key))

  # merge to single dataframe
  df = df_gva.merge(
    df_emp, on=["timestep", "lad_uk_2016"], how="left"
  ).merge(
    df_dwl, on=["timestep", "lad_uk_2016"], how="left"
  )

  # filter to include only Arc LADs
  df = df[df.lad_uk_2016.isin(arclads)].set_index(["timestep", "lad_uk_2016"])

  return df


def update_baseline_for_simim():
  df_emp = pd.read_csv("data/arc/arc_employment__baseline.csv")
  df_gva = pd.read_csv("data/arc/arc_gva__baseline.csv")

  # merge to single dataframe
  df = df_gva.merge(
    df_emp, on=["timestep", "lad_uk_2016"], how="left"
  )

  baseline_for_simim = df.reset_index().rename(columns={
    "timestep": "YEAR",
    "lad_uk_2016": "GEOGRAPHY_CODE",
    "employment": "JOBS",
    "gva": "GVA"
  })[[
     "YEAR", "GEOGRAPHY_CODE", "JOBS", "GVA"
  ]]
  baseline_for_simim["GVA"] = baseline_for_simim["GVA"].round(6)
  # convert from 1000s jobs to jobs
  baseline_for_simim["JOBS"] = (baseline_for_simim["JOBS"] * 1000).round().astype(int)
  baseline_for_simim.to_csv('./data/arc/arc_economic_baseline_for_simim.csv', index=False)


if __name__ == '__main__':
  main()
