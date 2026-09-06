


T7_HARDWARE = {
    "DIO0": {
        "name": "FIO0",
        "dio_name": "DIO0",
        "pwm_out" : True,
        "pwm_out_with_phase": True,
        "pulse_out": True,
        "frequency_in": True,
        "pulse_width_in": True,
        "line_to_line_in": True,
        "high_speed_counter": False,
        "interrupt_counter": True,
        "interrupt_counter_with_debounce": True,
        "quadrature_in": True,
        "interrupt_frequency_in": True,
        "conditional_reset": True,
        "digitial": True,
        "analog": False,
        "analog_ranges": [],
        "screw_terminal": True,
        "dsub": ("DB37",6)
    },
    "AIN0": {
        "name": "AIN0",
        "dio_name": "",
        "pwm_out" : False,
        "pwm_out_with_phase": False,
        "pulse_out": False,
        "frequency_in": False,
        "pulse_width_in": False,
        "line_to_line_in": False,
        "high_speed_counter": False,
        "interrupt_counter": False,
        "interrupt_counter_with_debounce": False,
        "quadrature_in": False,
        "interrupt_frequency_in": False,
        "conditional_reset": False,
        "digitial": False,
        "analog": True,
        "analog_ranges": [10, 1, 0.1, 0.01],
        "screw_terminal": True,
        "dsub": ("DB37",37)
    }
}
