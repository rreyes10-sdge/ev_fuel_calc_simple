import csv
from datetime import datetime, date, timedelta
from static_data import fossil_fuel_mpg_mapping, TOU_DATA
import json
import calendar
import math
import ast

 
INPUT_CSV = 'input.csv'
OUTPUT_CSV = 'output.csv'
SECOND_OUTPUT_CSV = 'extended_output.csv'

def determine_season(year: int, month: int, tou_seasons: dict) -> str:
    # Parse season date ranges
    summer_start = date(year, 6, 1)
    summer_end = date(year, 10, 31)
    current_date = date(year, month, 15)  # use middle of the month to avoid day issues
 
    if summer_start <= current_date <= summer_end:
        return "Summer"
    else:
        return "Winter"
    
def parse_time_str(time_str):
    return datetime.strptime(time_str, "%H:%M").time()
 
def get_tou_segments_for_day_type(tou_data, day_type, season):
    segments = {}
    for category, time_ranges in tou_data["TOU"][day_type][season].items():
        if isinstance(time_ranges, list):
            # Convert ["06:00-16:00", "21:00-00:00"] to tuples
            segments[category] = [tuple(tr.split('-')) for tr in time_ranges]
        else:
            # Single range like "16:00-21:00"
            segments[category] = [tuple(time_ranges.split('-'))]
    return segments

def time_to_datetime(t):
    return datetime.strptime(t, "%H:%M")

def get_day_type(day_name):
    return "WeekendsAndHolidays" if day_name in ["Saturday", "Sunday"] else "Weekdays"

def get_tou_hours(start_time_str, end_time_str, season, day_type, tou_data, tdven, charger_kw, allowed_periods):
    # Parse start and end times as datetime
    start_dt = time_to_datetime(start_time_str)
    end_dt = time_to_datetime(end_time_str)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)  # handle wraparound to next day

    total_hours = {
        "On-Peak": 0,
        "Off-Peak": 0,
        "Super Off-Peak": 0
    }

    segments = get_tou_segments_for_day_type(tou_data, day_type, season)
    remaining_energy = tdven

    # Iterate over each hour in the time range
    current = start_dt
    while current < end_dt and remaining_energy > 0:
        next_hour = current + timedelta(hours=1)
        current_time = current.time()

        for category, time_ranges in segments.items():
            if category not in allowed_periods:
                continue
            for start, end in time_ranges:
                start_seg = datetime.combine(current.date(), parse_time_str(start))
                end_seg = datetime.combine(current.date(), parse_time_str(end))
                if end_seg <= start_seg:
                    end_seg += timedelta(days=1)
                
                if start_seg <= current < end_seg:
                    total_hours[category] += 1
                    remaining_energy -= charger_kw
                    break
        current = next_hour

    return total_hours


def get_total_tou_hours_for_day(data, day, season, tou_data, tdven, charger_kw, allowed_periods):
    day_type = get_day_type(day)
    return get_tou_hours(
        start_time_str=data["charging_behavior_startTime"],
        end_time_str=data["charging_behavior_endTime"],
        season=season,
        day_type=day_type,
        tou_data=tou_data,
        tdven=tdven,
        charger_kw=charger_kw,
        allowed_periods=allowed_periods
    )


def generate_days_in_month(year, month):
    num_days = calendar.monthrange(year, month)[1]
    return [date(year, month, day).strftime("%A") for day in range(1, num_days + 1)]

def calculate_tou_hours_with_cutoff(tdven, charger_kw, tou_hours, allowed_periods):
    total_hours = {"On-Peak": 0, "Off-Peak": 0, "Super Off-Peak": 0}
    remaining_energy = tdven

    for period in allowed_periods:
        if remaining_energy <= 0:
            break
        hours = tou_hours[period]
        energy_needed = hours * charger_kw
        if remaining_energy <= energy_needed:
            total_hours[period] += remaining_energy / charger_kw
            remaining_energy = 0
        else:
            total_hours[period] += hours
            remaining_energy -= energy_needed

    return total_hours

# def get_total_tou_hours_for_period(data, year, month, tou_data, scenario, tdven, charger_kw):
#     season = determine_season(year, month, TOU_DATA["Seasons"])
#     all_days_in_month = generate_days_in_month(year, month)
#     active_days = [
#         day for day in all_days_in_month
#         if str(data['charging_behavior_days'].get(day, 'false')).lower() in ['true', '1']
#     ]

#     total_tou_hours = {"On-Peak": 0, "Off-Peak": 0, "Super Off-Peak": 0}
    
#     for day in active_days:
#         if scenario == "scenario_2" or scenario == "scenario_4":
#             allowed_periods = ["Off-Peak", "Super Off-Peak"]
#         else:
#             allowed_periods = ["On-Peak", "Off-Peak", "Super Off-Peak"]

#         daily_tou_hours = get_total_tou_hours_for_day(data, day, season, tou_data, tdven, charger_kw, allowed_periods)
#         total_tou_hours["On-Peak"] += daily_tou_hours["On-Peak"]
#         total_tou_hours["Off-Peak"] += daily_tou_hours["Off-Peak"]
#         total_tou_hours["Super Off-Peak"] += daily_tou_hours["Super Off-Peak"]
    
#     return total_tou_hours

def get_total_tou_hours_for_period(data, year, month, tou_data, scenario, tdven, charger_kw):
    season = determine_season(year, month, TOU_DATA["Seasons"])
    all_days_in_month = generate_days_in_month(year, month)
    active_days = [
        day for day in all_days_in_month
        if str(data['charging_behavior_days'].get(day, 'false')).lower() in ['true', '1']
    ]
 
    total_tou_hours = {"On-Peak": 0, "Off-Peak": 0, "Super Off-Peak": 0}
 
    if scenario == "scenario_2" or scenario == "scenario_4":
        allowed_periods = ["Off-Peak", "Super Off-Peak"]
    else:
        allowed_periods = ["On-Peak", "Off-Peak", "Super Off-Peak"]
 
    for day in active_days:
        day_type = get_day_type(day)
        daily_hours = get_tou_hours(
            start_time_str=data["charging_behavior_startTime"],
            end_time_str=data["charging_behavior_endTime"],
            season=season,
            day_type=day_type,
            tou_data=tou_data,
            tdven=tdven,
            charger_kw=charger_kw,
            allowed_periods=allowed_periods
        )
 
        for period in total_tou_hours:
            total_tou_hours[period] += daily_hours[period]
 
    return total_tou_hours

def service_fee(power_requirement, year):
    year_data = TOU_DATA["TOU_Rates"].get(str(year), {})
    service_fee_data = year_data.get("ServiceFee", {'ServiceFeeLess': 213.30, 'ServiceFeeMore': 766.91})
    
    if power_requirement <= 500:
        return service_fee_data['ServiceFeeLess']
    else:
        return service_fee_data['ServiceFeeMore']
    
def subscription_fee(power_requirement, year):
    year_data = TOU_DATA["TOU_Rates"].get(str(year), {})
    subscription_fee_data = year_data.get("SubscriptionFee", {'SubscriptionFeeLess': 48.33, 'SubscriptionFeeMore': 120.85})
    
    if power_requirement <= 150:
        fee = subscription_fee_data['SubscriptionFeeLess'] * (power_requirement / 10)
    else:
        fee = subscription_fee_data['SubscriptionFeeMore'] * (power_requirement / 25)
    
    # Round up to the nearest cent
    fee = math.ceil(fee * 100) / 100
    return fee

    
def calculate_commodity_distribution_cost(power_requirement, tou_hours, season, year, day_type, tou_data):
    rates = tou_data["TOU_Rates"][str(year)][day_type][season]
    cost = (
        power_requirement * tou_hours["On-Peak"] * rates["On-Peak"]["Total"] +
        power_requirement * tou_hours["Off-Peak"] * rates["Off-Peak"]["Total"] +
        power_requirement * tou_hours["Super Off-Peak"] * rates["Super_Off-Peak"]["Total"]
    )
    return cost

def process_row(data):
    # Parse and transform inputs from CSV row
    year = int(data.get("year", 2025))
    month_input = data.get("month", 4)

    if isinstance(month_input, str) and not month_input.isdigit():
        try:
            month = list(calendar.month_name).index(month_input.strip())
        except ValueError:
            raise ValueError(f"Invalid month name: {month_input}")
    else:
        month = int(month_input)

    # Determine TOU season using helper
    season = determine_season(year, month, TOU_DATA["Seasons"])

    total_daily_miles_driven = 0
    total_num_vehicles = 0

    vehicle_groups = []
    for i in range(1, 6):
        vehicle_class = data.get(f"vehicle_group_{i}_class")
        num_vehicles = int(data.get(f"vehicle_group_{i}_num") or 0)
        avg_daily_mileage = int(data.get(f"vehicle_group_{i}_mileage") or 0)
        if vehicle_class and num_vehicles > 0:
            vehicle_groups.append({
                "vehicle_class": vehicle_class,
                "num_vehicles": num_vehicles,
                "avg_daily_mileage": avg_daily_mileage
            })
            total_num_vehicles += num_vehicles
            total_daily_miles_driven += avg_daily_mileage * num_vehicles
 
    charger_groups = []
    for i in range(1, 6):
        num_chargers = int(data.get(f"charger_group_{i}_num") or 0)
        charger_kw = int(data.get(f"charger_group_{i}_kw") or 0)
        if num_chargers > 0:
            charger_groups.append({
                "num_chargers": num_chargers,
                "charger_kw": charger_kw
            })

    total_num_chargers = 0
    total_charger_capacity = 0

    for i in range(1, 6):
        num_chargers = int(data.get(f"charger_group_{i}_num") or 0)
        charger_kw = int(data.get(f"charger_group_{i}_kw") or 0)
        if num_chargers > 0:
            charger_groups.append({
                "num_chargers": num_chargers,
                "charger_kw": charger_kw
            })
            total_num_chargers += num_chargers
            total_charger_capacity += num_chargers * charger_kw
    base_year = 2025
    # Calculate the number of years since the base year
    years_since_base = year - base_year

    fossil_fuel_price = float(data.get("fossil_fuel_price", 4.30) or 4.30)
    fossil_fuel_multiplier = float(data.get("fossil_fuel_multiplier", 1.0131) or 1.0131)
    fossil_fuel_mpg_override = data.get("fossil_fuel_efficiency")
    transformer_capacity = float(data.get("transformer_capacity", 0) or 0)

    adjusted_fossil_fuel_price = fossil_fuel_price * ((fossil_fuel_multiplier) ** years_since_base)


    # Parse the charging_behavior_days field
    if 'charging_behavior_days' in data and data['charging_behavior_days']:
        try:
            data['charging_behavior_days'] = ast.literal_eval(data['charging_behavior_days'])
        except (ValueError, SyntaxError):
            print("⚠️ Could not parse 'charging_behavior_days'")
            data['charging_behavior_days'] = {}
    
    # Example: Count number of "True" days
    # active_days = [
    #     day for day, is_active in data['charging_behavior_days'].items()
    #     if str(is_active).lower() in ['true', '1']
    # ]
    # num_days = len(active_days)

    all_days_in_month = generate_days_in_month(year, month)
    active_days = [
        day for day in all_days_in_month
        if str(data['charging_behavior_days'].get(day, 'false')).lower() in ['true', '1']
    ]

    def count_days_in_month(year, month, active_days):
        day_name_to_index = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2,
            "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        c = calendar.Calendar()
        count = 0
        for day in c.itermonthdays2(year, month):
            day_num, weekday = day
            if day_num != 0 and weekday in [day_name_to_index[d] for d in active_days]:
                count += 1
        return count

    # Calculate TDVEN (Total Daily Vehicle Energy Needed)
    tdven = 0
    total_mpg = 0
    for group in vehicle_groups:
        vehicle_class = group["vehicle_class"]
        num_vehicles = group["num_vehicles"]
        mileage = group["avg_daily_mileage"]
    
        efficiency_data = fossil_fuel_mpg_mapping.get(vehicle_class)
        if efficiency_data:
            miles_per_kwh = efficiency_data["mile_per_kwh"]
            tdven += num_vehicles * mileage / miles_per_kwh
            mpg = efficiency_data["mpg"]
            total_mpg += mpg * num_vehicles
        else:
            print(f"Warning: Efficiency data not found for vehicle class '{vehicle_class}'")

    if fossil_fuel_mpg_override:
        try:
            fossil_fuel_mpg_override = float(fossil_fuel_mpg_override)
            average_mpg = fossil_fuel_mpg_override
        except ValueError:
            print("Warning: Invalid fossil_fuel_efficiency value, using calculated average MPG")
            average_mpg = total_mpg / total_num_vehicles if total_num_vehicles > 0 else 15
    else:
        average_mpg = total_mpg / total_num_vehicles if total_num_vehicles > 0 else 15

    

    # print(tdven)
    # print(total_charger_capacity)

    # Calculate TOU hours for the first active day
    first_day_tou_hours = {"On-Peak": 0, "Off-Peak": 0, "Super Off-Peak": 0}
    first_active_day = active_days[0] if active_days else None

    if first_active_day:
        first_day_tou_hours = get_total_tou_hours_for_day(data, first_active_day, season, TOU_DATA, tdven, charger_kw, ["On-Peak", "Off-Peak", "Super Off-Peak"])
    else:
        print(f"⚠️ Warning: No active charging days specified for {month}/{year} — skipping power requirement calculations may lead to divide by zero.")
 

    # Calculate total TOU hours for the entire month given each scenario
    total_tou_hours_scenario_1 = get_total_tou_hours_for_period(data, year, month, TOU_DATA, "scenario_1", tdven, charger_kw)
    total_tou_hours_scenario_2 = get_total_tou_hours_for_period(data, year, month, TOU_DATA, "scenario_2", tdven, charger_kw)
    total_tou_hours_scenario_3 = get_total_tou_hours_for_period(data, year, month, TOU_DATA, "scenario_3", tdven, total_charger_capacity)
    total_tou_hours_scenario_4 = get_total_tou_hours_for_period(data, year, month, TOU_DATA, "scenario_4", tdven, total_charger_capacity)

    # first day tou hours since we power requirement is measured hourly and the total tou hours sums total hours for full month. tdven is daily energy, thus we only calculate using tou hours for one day, in this case the first active day user specified
    def safe_divide(numerator, denominator, fallback=0):
        return numerator / denominator if denominator else fallback
 
    power_requirements = {
        "scenario_1": safe_divide(tdven, first_day_tou_hours["On-Peak"] + first_day_tou_hours["Off-Peak"] + first_day_tou_hours["Super Off-Peak"]),
        "scenario_2": safe_divide(tdven, first_day_tou_hours["Off-Peak"] + first_day_tou_hours["Super Off-Peak"]),
        "scenario_3": total_charger_capacity,
        "scenario_4": total_charger_capacity
    }

    # Monthly EV Cost compilations start here
    # basic service fee
    fee = {
        "scenario_1": service_fee(power_requirements['scenario_1'], year),
        "scenario_2": service_fee(power_requirements['scenario_2'], year),
        "scenario_3": service_fee(power_requirements['scenario_3'], year),
        "scenario_4": service_fee(power_requirements['scenario_4'], year)
    }
    
    # subscription fee
    sub_fee = {
        "scenario_1": subscription_fee(power_requirements['scenario_1'], year),
        "scenario_2": subscription_fee(power_requirements['scenario_2'], year),
        "scenario_3": subscription_fee(power_requirements['scenario_3'], year),
        "scenario_4": subscription_fee(power_requirements['scenario_4'], year)
    }

    # commodity distribution costs
    commodity_distribution_cost = {
        "scenario_1": calculate_commodity_distribution_cost(power_requirements["scenario_1"], total_tou_hours_scenario_1, season, year, get_day_type(first_active_day), TOU_DATA),
        "scenario_2": calculate_commodity_distribution_cost(power_requirements["scenario_2"], total_tou_hours_scenario_2, season, year, get_day_type(first_active_day), TOU_DATA),
        "scenario_3": calculate_commodity_distribution_cost(power_requirements["scenario_3"], total_tou_hours_scenario_3, season, year, get_day_type(first_active_day), TOU_DATA),
        "scenario_4": calculate_commodity_distribution_cost(power_requirements["scenario_4"], total_tou_hours_scenario_4, season, year, get_day_type(first_active_day), TOU_DATA)
    }

    # tc = total cost = sum (service fee + sub fee + commodity distribution )
    electric_monthly_tc = {
        "scenario_1": fee["scenario_1"] + sub_fee["scenario_1"] + commodity_distribution_cost["scenario_1"],
        "scenario_2": fee["scenario_2"] + sub_fee["scenario_2"] + commodity_distribution_cost["scenario_2"],
        "scenario_3": fee["scenario_3"] + sub_fee["scenario_3"] + commodity_distribution_cost["scenario_3"],
        "scenario_4": fee["scenario_4"] + sub_fee["scenario_4"] + commodity_distribution_cost["scenario_4"]
    }

    # fossil fuel calculations
    total_monthly_miles_driven = total_daily_miles_driven * count_days_in_month(year,month,active_days)
    monthly_fossil_fuel_tc = (total_monthly_miles_driven / average_mpg) * adjusted_fossil_fuel_price

    # optional settings and miscellaneous calculations

    # charger coverage check flags per scenario
    # scenario 2 and 4 allow on-peak charging (unmanaged scenarios)
    # scenario 1 and 3 do not allow on-peak charging (optimal/managed scenarios)
    total_daily_charger_energy_output_with_onpeak = total_charger_capacity * (first_day_tou_hours["On-Peak"] + first_day_tou_hours["Off-Peak"] + first_day_tou_hours["Super Off-Peak"])
    total_daily_charger_energy_output_without_onpeak = total_charger_capacity * (first_day_tou_hours["Off-Peak"] + first_day_tou_hours["Super Off-Peak"])

    charger_cover_scenarios_2_and_4 = 'true' if total_daily_charger_energy_output_with_onpeak >= tdven else 'false'
    charger_cover_scenarios_1_and_3 = 'true' if total_daily_charger_energy_output_without_onpeak >= tdven else 'false'
    # print("tdven", tdven, "umanaged capacity", total_daily_charger_energy_output_with_onpeak, "managed capacity", total_daily_charger_energy_output_without_onpeak, "unamanged", charger_cover_scenarios_2_and_4, "managed", charger_cover_scenarios_1_and_3)
    
    available_transformer_capacity_check = 'true' if transformer_capacity > power_requirements["scenario_3"] else 'false'
    # print(transformer_capacity,power_requirements["scenario_3"],available_transformer_capacity_check)
    return {
        "total_vehicles": total_num_vehicles,
        "total daily miles driven": total_daily_miles_driven,
        "total_chargers": total_num_chargers,
        "charging_days_count": count_days_in_month(year,month,active_days),
        "tou_season": season,
        "TDVEN": round(tdven, 2),
        "first_active_daily_tou_hours": first_day_tou_hours,
        "total_month_tou_hours": {
            "scenario_1": total_tou_hours_scenario_1,
            "scenario_2": total_tou_hours_scenario_2,
            "scenario_3": total_tou_hours_scenario_3,
            "scenario_4": total_tou_hours_scenario_4
        },
        "scenario_1": {"power_requirement": power_requirements["scenario_1"], "basic service fee": fee["scenario_1"], "subscription fee": sub_fee["scenario_1"], "commodity distribution cost": commodity_distribution_cost["scenario_1"], "electric monthly tc": electric_monthly_tc["scenario_1"]},
        "scenario_2": {"power_requirement": power_requirements["scenario_2"], "basic service fee": fee["scenario_2"], "subscription fee": sub_fee["scenario_2"], "commodity distribution cost": commodity_distribution_cost["scenario_2"], "electric monthly tc": electric_monthly_tc["scenario_2"]},
        "scenario_3": {"power_requirement": power_requirements["scenario_3"], "basic service fee": fee["scenario_3"], "subscription fee": sub_fee["scenario_3"], "commodity distribution cost": commodity_distribution_cost["scenario_3"], "electric monthly tc": electric_monthly_tc["scenario_3"]},
        "scenario_4": {"power_requirement": power_requirements["scenario_4"], "basic service fee": fee["scenario_4"], "subscription fee": sub_fee["scenario_4"], "commodity distribution cost": commodity_distribution_cost["scenario_4"], "electric monthly tc": electric_monthly_tc["scenario_4"]},
        "fossil_fuel_average_mpg": average_mpg,
        "adjusted_fossil_fuel_price": round(adjusted_fossil_fuel_price,2),
        "monthly_fossil_fuel_tc": round(monthly_fossil_fuel_tc,2),
        "error_checks": {
            "charger_cover_scenarios_2_and_4_flag": charger_cover_scenarios_2_and_4,
            "charger_cover_scenarios_1_and_3_flag": charger_cover_scenarios_1_and_3,
            "available_transformer_capacity_flag": available_transformer_capacity_check
        }
    }
    


def process_all_years_months(data):
    results = []
    original_charging_behavior_days = data.get('charging_behavior_days')
    original_start_time = data.get('charging_behavior_startTime')
    original_end_time = data.get('charging_behavior_endTime')

    for year in range(2025, 2033):
        for month in range(1, 13):
            # Update the data dictionary with the current year and month
            data_copy = data.copy()
            data_copy["year"] = year
            data_copy["month"] = month
            
            data_copy['charging_behavior_days'] = original_charging_behavior_days
            data_copy['charging_behavior_startTime'] = original_start_time
            data_copy['charging_behavior_endTime'] = original_end_time


            # Process the row for the current year and month
            result = process_row(data_copy)

            # Add the year and month to the result
            result["year"] = year
            result["month"] = month

            # Append the result to the results list
            results.append(result)

    return results




def main():
    with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        output_rows = []
        extended_output_rows = []
        for row in rows:
            # Process the current row for the original output
            result = process_row(row)
            row.update(result)
            output_rows.append(row)

            # Process all years and months for the extended output
            # extended_results = process_all_years_months(row)
            # extended_output_rows.extend(extended_results)

        # Write to the original output CSV
        fieldnames = output_rows[0].keys()
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        # Write to the second output CSV
        # extended_fieldnames = extended_output_rows[0].keys()
        # with open(SECOND_OUTPUT_CSV, 'w', newline='', encoding='utf-8') as extended_outfile:
        #     extended_writer = csv.DictWriter(extended_outfile, fieldnames=extended_fieldnames)
        #     extended_writer.writeheader()
        #     extended_writer.writerows(extended_output_rows)

if __name__ == "__main__":
    main()



# def main():
#     with open(INPUT_CSV, newline='', encoding='utf-8') as infile:
#         reader = csv.DictReader(infile)
#         rows = list(reader)

#     output_rows = []
#     for row in rows:
#         result = process_row(row)
#         row.update(result)  # Add the new calculated fields to the original row
#         output_rows.append(row)

#     fieldnames = output_rows[0].keys()

#     with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as outfile:
#         writer = csv.DictWriter(outfile, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(output_rows)
 
# if __name__ == "__main__":
#     main()