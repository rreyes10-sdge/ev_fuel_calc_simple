# ev_fuel_calc_simple
Used for test scenarios for given month

Utilize the input.csv to create additional scenarios to check calculations against.

output.csv will contain new columns per row that contain the following information that the ev_calc_simple.py calculates:
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
