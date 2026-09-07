import CoolProp.CoolProp as CP
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.title("🧪 Chemical Property Prediction Micro-Tool")
st.write(
    "Commercial MVP for pure fluids, binary mixtures, multi-EOS thermodynamic"
    " modeling (vDW, RK, SRK, PR, Generic), Wilson activity coefficients, and"
    " phase envelopes."
)

# Sidebar mode selection
st.sidebar.header("Operating Mode")
mode = st.sidebar.radio(
    "Select Mode",
    [
        "Pure Component Analysis",
        "Binary Mixture & VLE",
        "Multi-EOS & Cubic Models",
        "Activity Coefficients (Wilson Model)",
    ],
)

if mode == "Pure Component Analysis":
  st.sidebar.header("Pure Fluid Conditions")
  fluid_options = [
      "Water",
      "Ethanol",
      "Methane",
      "Propane",
      "Acetone",
      "Benzene",
      "Toluene",
  ]
  selected_fluid = st.sidebar.selectbox("Select Compound", fluid_options)

  system_mass = st.sidebar.number_input(
      "System Mass (kg)", min_value=0.01, max_value=100.0, value=1.0, step=0.1
  )

  temp_c = st.sidebar.slider(
      "Temperature (°C)", min_value=0.0, max_value=150.0, value=25.0, step=1.0
  )
  temp_k = temp_c + 273.15

  pressure_bar = st.sidebar.slider(
      "Pressure (bar)", min_value=0.5, max_value=50.0, value=1.0, step=0.5
  )
  pressure = pressure_bar * 100000.0

  st.subheader(f"Spot Results for {selected_fluid} at {pressure_bar} bar")

  try:
    as_state = CP.AbstractState("HEOS", selected_fluid)
    as_state.update(CP.PT_INPUTS, pressure, temp_k)

    density = as_state.rhomass()
    enthalpy = as_state.hmass() / 1000.0
    viscosity = as_state.viscosity()
    fugacity = as_state.fugacity(0) / 100000.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Density", f"{density:.2f}", "kg/m³")
    col2.metric("Enthalpy", f"{enthalpy:.2f}", "kJ/kg")
    col3.metric("Viscosity", f"{viscosity:.5f}", "Pa·s")
    col4.metric("Fugacity", f"{fugacity:.2f}", "bar")

    st.markdown("---")
    st.subheader("⚙️ Advanced Process Engineering Metrics")

    z_factor = CP.PropsSI("Z", "T", temp_k, "P", pressure, selected_fluid)
    b_virial = as_state.second_virial_coefficient()
    c_virial = as_state.third_virial_coefficient()

    try:
      h_liq = CP.PropsSI("H", "T", temp_k, "Q", 0, selected_fluid) / 1000.0
      h_vap = CP.PropsSI("H", "T", temp_k, "Q", 1, selected_fluid) / 1000.0
      latent_heat = h_vap - h_liq
    except:
      latent_heat = np.nan

    eng_col1, eng_col2, eng_col3, eng_col4 = st.columns(4)
    eng_col1.metric("Compressibility (Z)", f"{z_factor:.4f}")
    if not np.isnan(latent_heat):
      eng_col2.metric("Latent Heat", f"{latent_heat:.2f}", "kJ/kg")
    else:
      eng_col2.metric("Latent Heat", "N/A")
    eng_col3.metric("2nd Virial (B)", f"{b_virial:.5f}", "m³/mol")
    eng_col4.metric("3rd Virial (C)", f"{c_virial:.6f}", "m⁶/mol²")

  except Exception as e:
    st.error(f"Calculation error: {e}")

  st.markdown("---")
  st.subheader("📊 Thermodynamic Phase Diagrams & Trends")
  diagram_choice = st.selectbox(
      "Choose Visualization",
      [
          "Pressure-Volume (P-v) Saturation Dome",
          "Temperature-Entropy (T-s) Saturation Envelope",
          "Density Variation Curve (Isobaric)",
      ],
  )

  try:
    if diagram_choice == "Pressure-Volume (P-v) Saturation Dome":
      t_crit = CP.PropsSI(selected_fluid, "Tcrit")
      t_min = CP.PropsSI(selected_fluid, "Tmin") + 5
      t_sweep = np.linspace(t_min, t_crit - 0.1, 60)

      v_liq = [
          system_mass * (1.0 / CP.PropsSI("D", "T", t, "Q", 0, selected_fluid))
          for t in t_sweep
      ]
      v_vap = [
          system_mass * (1.0 / CP.PropsSI("D", "T", t, "Q", 1, selected_fluid))
          for t in t_sweep
      ]
      p_vals = [
          CP.PropsSI("P", "T", t, "Q", 0, selected_fluid) / 100000.0
          for t in t_sweep
      ]

      v_dome = v_liq + v_vap[::-1]
      p_dome = p_vals + p_vals[::-1]

      df_plot = pd.DataFrame(
          {"Total Volume (m³)": v_dome, "Pressure (bar)": p_dome}
      )
      fig = px.line(
          df_plot,
          x="Total Volume (m³)",
          y="Pressure (bar)",
          title=f"P-v Saturation Dome for {selected_fluid} (Mass = {system_mass} kg)",
      )
      fig.update_xaxes(type="log")
      st.plotly_chart(fig, use_container_width=True)

    elif diagram_choice == "Temperature-Entropy (T-s) Saturation Envelope":
      t_crit = CP.PropsSI(selected_fluid, "Tcrit")
      t_min = CP.PropsSI(selected_fluid, "Tmin") + 15
      t_sweep = np.linspace(t_min, t_crit - 1.0, 45)
      s_liq = [
          CP.PropsSI("Smass", "T", t, "Q", 0, selected_fluid) / 1000.0
          for t in t_sweep
      ]
      s_vap = [
          CP.PropsSI("Smass", "T", t, "Q", 1, selected_fluid) / 1000.0
          for t in t_sweep
      ]
      t_celsius = [t - 273.15 for t in t_sweep]
      df_plot = pd.DataFrame({
          "Temperature (°C)": t_celsius * 2,
          "Specific Entropy (kJ/kg·K)": s_liq + s_vap,
          "Phase": ["Saturated Liquid"] * len(t_sweep)
          + ["Saturated Vapor"] * len(t_sweep),
      })
      fig = px.line(
          df_plot,
          x="Specific Entropy (kJ/kg·K)",
          y="Temperature (°C)",
          color="Phase",
          markers=True,
          title=f"T-s Saturation Envelope for {selected_fluid}",
      )
      st.plotly_chart(fig, use_container_width=True)

    else:
      t_range_c = np.linspace(10, 140, 40)
      densities = [
          CP.PropsSI("D", "T", t + 273.15, "P", pressure, selected_fluid)
          for t in t_range_c
      ]
      df_plot = pd.DataFrame(
          {"Temperature (°C)": t_range_c, "Density (kg/m³)": densities}
      )
      fig = px.line(
          df_plot,
          x="Temperature (°C)",
          y="Density (kg/m³)",
          markers=True,
          title=f"Density Variation at {pressure_bar} bar",
      )
      st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        label="📥 Download Plotted Data as CSV",
        data=df_plot.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected_fluid}_thermo_data.csv",
        mime="text/csv",
    )
  except Exception as e:
    st.info(f"Could not render curve: {e}")

elif mode == "Binary Mixture & VLE":
  st.sidebar.header("Binary Mixture Conditions")
  mix_options = [
      ("Ethanol & Water", "Ethanol&Water"),
      ("Methane & Propane", "Methane&Propane"),
      ("Benzene & Toluene", "Benzene&Toluene"),
  ]
  mix_name, mix_string = st.sidebar.selectbox("Select Mixture", mix_options)

  x1 = st.sidebar.slider(
      f"Mole Fraction ({mix_name.split('&')[0].strip()})",
      min_value=0.05,
      max_value=0.95,
      value=0.5,
      step=0.05,
  )
  mix_pressure_bar = st.sidebar.slider(
      "System Pressure (bar)", min_value=0.5, max_value=10.0, value=1.0, step=0.1
  )
  mix_pressure = mix_pressure_bar * 100000.0

  st.subheader(f"Binary Mixture: {mix_name} (x1 = {x1})")

  try:
    mix_state = CP.AbstractState("HEOS", mix_string)
    mix_state.set_mole_fractions([x1, 1.0 - x1])

    mix_state.update(CP.PQ_INPUTS, mix_pressure, 0.0)
    bubble_temp = mix_state.T() - 273.15

    mix_state.update(CP.PQ_INPUTS, mix_pressure, 1.0)
    dew_temp = mix_state.T() - 273.15

    col1, col2 = st.columns(2)
    col1.metric("Bubble Point Temperature", f"{bubble_temp:.2f}", "°C")
    col2.metric("Dew Point Temperature", f"{dew_temp:.2f}", "°C")

    st.markdown("---")
    st.subheader("📈 Composition Sweep: Mole Fraction vs. Saturation Temperatures")

    x_sweep = np.linspace(0.05, 0.95, 20)
    tb_list = []
    td_list = []

    for val in x_sweep:
      temp_state = CP.AbstractState("HEOS", mix_string)
      temp_state.set_mole_fractions([val, 1.0 - val])
      try:
        temp_state.update(CP.PQ_INPUTS, mix_pressure, 0.0)
        tb_list.append(temp_state.T() - 273.15)
        temp_state.update(CP.PQ_INPUTS, mix_pressure, 1.0)
        td_list.append(temp_state.T() - 273.15)
      except:
        tb_list.append(np.nan)
        td_list.append(np.nan)

    df_mix = pd.DataFrame({
        "Mole Fraction (x1)": x_sweep,
        "Bubble Point (°C)": tb_list,
        "Dew Point (°C)": td_list,
    })

    fig_mix = px.line(
        df_mix,
        x="Mole Fraction (x1)",
        y=["Bubble Point (°C)", "Dew Point (°C)"],
        markers=True,
        title=f"Phase Envelope (T-x-y) for {mix_name} at {mix_pressure_bar} bar",
    )
    st.plotly_chart(fig_mix, use_container_width=True)

    st.download_button(
        label="📥 Download Mixture VLE Data as CSV",
        data=df_mix.to_csv(index=False).encode("utf-8"),
        file_name=f"{mix_name.replace('&', 'and').replace(' ', '')}_vle_data.csv",
        mime="text/csv",
    )

  except Exception as e:
    st.error(
        "Could not solve mixture equilibrium at these conditions. Details:"
        f" {e}"
    )

elif mode == "Multi-EOS & Cubic Models":
  st.sidebar.header("Cubic EOS Configuration")
  eos_choice = st.sidebar.selectbox(
      "Select Equation of State",
      [
          "van der Waals (vDW)",
          "Redlich-Kwong (RK)",
          "Soave-Redlich-Kwong (SRK)",
          "Peng-Robinson (PR)",
          "Generic Cubic EOS",
      ],
  )

  fluid_list = ["Ethanol", "Water", "Methane", "Propane", "Benzene", "Toluene"]
  comp1 = st.sidebar.selectbox("Component 1", fluid_list, index=0)
  comp2 = st.sidebar.selectbox("Component 2", fluid_list, index=1)

  x1_eos = st.sidebar.slider(
      f"Mole Fraction {comp1} (y1)",
      min_value=0.05,
      max_value=0.95,
      value=0.5,
      step=0.05,
  )
  T_eos_c = st.sidebar.slider(
      "Temperature (°C)", min_value=0.0, max_value=200.0, value=50.0, step=1.0
  )
  P_eos_bar = st.sidebar.slider(
      "Pressure (bar)", min_value=0.5, max_value=50.0, value=5.0, step=0.5
  )

  u_gen, w_gen = 1.0, 0.0
  if eos_choice == "Generic Cubic EOS":
    st.sidebar.subheader("Generic EOS Parameters")
    u_gen = st.sidebar.number_input("Parameter u", value=1.0, step=0.1)
    w_gen = st.sidebar.number_input("Parameter w", value=0.0, step=0.1)

  T_eos = T_eos_c + 273.15
  P_eos = P_eos_bar * 100000.0
  R = 8.314

  eos_data = {
      "Water": {"Tc": 647.3, "Pc": 22.064e6, "omega": 0.3443},
      "Ethanol": {"Tc": 513.9, "Pc": 6.148e6, "omega": 0.6435},
      "Methane": {"Tc": 190.6, "Pc": 4.599e6, "omega": 0.0115},
      "Propane": {"Tc": 369.8, "Pc": 4.248e6, "omega": 0.1523},
      "Benzene": {"Tc": 562.2, "Pc": 4.894e6, "omega": 0.2120},
      "Toluene": {"Tc": 591.8, "Pc": 4.110e6, "omega": 0.2638},
  }

  st.subheader(f"{eos_choice}: {comp1} ({x1_eos}) + {comp2} ({1-x1_eos:.2f})")
  st.write(
      f"Calculates mixture compressibility ($Z$) and partial molar volumes"
      f" ($\\bar{{V}}_i$) using the **{eos_choice}** equation of state."
  )

  try:
    tc1, pc1, om1 = (
        eos_data[comp1]["Tc"],
        eos_data[comp1]["Pc"],
        eos_data[comp1]["omega"],
    )
    tc2, pc2, om2 = (
        eos_data[comp2]["Tc"],
        eos_data[comp2]["Pc"],
        eos_data[comp2]["omega"],
    )

    def get_eos_parameters(tc, pc, omega, model):
      if model == "van der Waals (vDW)":
        a = (27.0 / 64.0) * (R**2) * (tc**2) / pc
        b = (1.0 / 8.0) * R * tc / pc
        alpha = 1.0
      elif model == "Redlich-Kwong (RK)":
        a = 0.42748 * (R**2) * (tc**2.5) / pc
        b = 0.08664 * R * tc / pc
        alpha = (tc / T_eos) ** 0.5
      elif model == "Soave-Redlich-Kwong (SRK)":
        a = 0.42748 * (R**2) * (tc**2) / pc
        b = 0.08664 * R * tc / pc
        m = 0.480 + 1.574 * omega - 0.176 * (omega**2)
        alpha = (1.0 + m * (1.0 - np.sqrt(T_eos / tc))) ** 2
      elif model == "Peng-Robinson (PR)":
        a = 0.45724 * (R**2) * (tc**2) / pc
        b = 0.07780 * R * tc / pc
        m = 0.37464 + 1.54226 * omega - 0.26992 * (omega**2)
        alpha = (1.0 + m * (1.0 - np.sqrt(T_eos / tc))) ** 2
      else:  # Generic Cubic
        a = 0.45724 * (R**2) * (tc**2) / pc
        b = 0.07780 * R * tc / pc
        alpha = 1.0
      return a * alpha, b

    a1_val, b1_val = get_eos_parameters(tc1, pc1, om1, eos_choice)
    a2_val, b2_val = get_eos_parameters(tc2, pc2, om2, eos_choice)

    y1 = x1_eos
    y2 = 1.0 - y1
    a12 = np.sqrt(a1_val * a2_val)

    def get_total_volume(n1_val, n2_val):
      n_tot = n1_val + n2_val
      yy1 = n1_val / n_tot
      yy2 = n2_val / n_tot

      am = (yy1**2) * a1_val + 2 * yy1 * yy2 * a12 + (yy2**2) * a2_val
      bm = yy1 * b1_val + yy2 * b2_val

      A = (am * P_eos) / ((R**2) * (T_eos**2))
      B = (bm * P_eos) / (R * T_eos)

      if eos_choice == "van der Waals (vDW)":
        coeffs = [1.0, -(1.0 + B), A, -A * B]
      elif eos_choice in ["Redlich-Kwong (RK)", "Soave-Redlich-Kwong (SRK)"]:
        At = (
            (am * P_eos) / ((R**2) * (T_eos**2.5))
            if eos_choice == "Redlich-Kwong (RK)"
            else A
        )
        coeffs = (
            [1.0, -1.0, (At - B - B**2), -At * B]
            if eos_choice == "Redlich-Kwong (RK)"
            else [1.0, -1.0, (A - B - B**2), -A * B]
        )
      elif eos_choice == "Peng-Robinson (PR)":
        coeffs = [
            1.0,
            -(1.0 - B),
            (A - 3.0 * (B**2) - 2.0 * B),
            -(A * B - (B**2) - (B**3)),
        ]
      else:  # Generic Cubic using u, w
        coeffs = [
            1.0,
            -(1.0 - B),
            (A + w_gen * (B**2) - u_gen * B - u_gen * B * B),
            -(A * B + w_gen * (B**2) + w_gen * (B**3)),
        ]

      rt = np.roots(coeffs)
      rr = [r.real for r in rt if abs(r.imag) < 1e-6 and r.real > B]
      if not rr:
        return np.nan
      Z_val = max(rr)
      V_molar = Z_val * R * T_eos / P_eos
      return n_tot * V_molar

    n1_base = y1
    n2_base = y2
    V_base = get_total_volume(n1_base, n2_base)

    dn = 1e-4
    V_n1_up = get_total_volume(n1_base + dn, n2_base)
    V_n2_up = get_total_volume(n1_base, n2_base + dn)

    bar_V1 = (V_n1_up - V_base) / dn
    bar_V2 = (V_n2_up - V_base) / dn

    am_b = (y1**2) * a1_val + 2 * y1 * y2 * a12 + (y2**2) * a2_val
    bm_b = y1 * b1_val + y2 * b2_val
    A_b = (am_b * P_eos) / ((R**2) * (T_eos**2))
    B_b = (bm_b * P_eos) / (R * T_eos)

    if eos_choice == "van der Waals (vDW)":
      coeffs_b = [1.0, -(1.0 + B_b), A_b, -A_b * B_b]
    elif eos_choice in ["Redlich-Kwong (RK)", "Soave-Redlich-Kwong (SRK)"]:
      At_b = (
          (am_b * P_eos) / ((R**2) * (T_eos**2.5))
          if eos_choice == "Redlich-Kwong (RK)"
          else A_b
      )
      coeffs_b = (
          [1.0, -1.0, (At_b - B_b - B_b**2), -At_b * B_b]
          if eos_choice == "Redlich-Kwong (RK)"
          else [1.0, -1.0, (A_b - B_b - B_b**2), -A_b * B_b]
      )
    elif eos_choice == "Peng-Robinson (PR)":
      coeffs_b = [
          1.0,
          -(1.0 - B_b),
          (A_b - 3.0 * (B_b**2) - 2.0 * B_b),
          -(A_b * B_b - (B_b**2) - (B_b**3)),
      ]
    else:
      coeffs_b = [
          1.0,
          -(1.0 - B_b),
          (A_b + w_gen * (B_b**2) - u_gen * B_b - u_gen * B_b * B_b),
          -(A_b * B_b + w_gen * (B_b**2) + w_gen * (B_b**3)),
      ]

    rt_b = np.roots(coeffs_b)
    rr_b = [r.real for r in rt_b if abs(r.imag) < 1e-6 and r.real > B_b]
    Z_mix = max(rr_b) if rr_b else np.nan

    col1, col2, col3 = st.columns(3)
    col1.metric("Mixture Z Factor", f"{Z_mix:.4f}")
    col2.metric(f"Partial Molar Vol ({comp1})", f"{bar_V1*1e6:.2f}", "cm³/mol")
    col3.metric(f"Partial Molar Vol ({comp2})", f"{bar_V2*1e6:.2f}", "cm³/mol")

    st.markdown("---")
    st.subheader(f"📈 Composition Sweep: Partial Molar Volumes ({eos_choice})")
    sweep_y1 = np.linspace(0.05, 0.95, 25)
    bv1_list, bv2_list = [], []

    for val in sweep_y1:
      nn1 = val
      nn2 = 1.0 - val
      v_b = get_total_volume(nn1, nn2)
      v_1 = get_total_volume(nn1 + dn, nn2)
      v_2 = get_total_volume(nn1, nn2 + dn)
      bv1_list.append(((v_1 - v_b) / dn) * 1e6)
      bv2_list.append(((v_2 - v_b) / dn) * 1e6)

    df_eos = pd.DataFrame({
        f"Mole Fraction {comp1} (y1)": sweep_y1,
        f"Partial Molar Vol {comp1} (cm³/mol)": bv1_list,
        f"Partial Molar Vol {comp2} (cm³/mol)": bv2_list,
    })

    fig_eos = px.line(
        df_eos,
        x=f"Mole Fraction {comp1} (y1)",
        y=[
            f"Partial Molar Vol {comp1} (cm³/mol)",
            f"Partial Molar Vol {comp2} (cm³/mol)",
        ],
        markers=True,
        title=f"Partial Molar Volumes for {comp1} - {comp2} at {P_eos_bar} bar,"
        f" {T_eos_c}°C ({eos_choice})",
    )
    st.plotly_chart(fig_eos, use_container_width=True)

    st.download_button(
        label=f"📥 Download {eos_choice} Data as CSV",
        data=df_eos.to_csv(index=False).encode("utf-8"),
        file_name=f"{comp1}_{comp2}_{eos_choice.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
  except Exception as e:
    st.error(f"Equation of state calculation error: {e}")

else:
  st.sidebar.header("Wilson Activity Model")
  wilson_pairs = [
      ("Ethanol & Water", "Ethanol", "Water", 1045.0, 3750.0, 58.6, 18.0),
      ("Benzene & Toluene", "Benzene", "Toluene", -150.0, 180.0, 89.4, 106.8),
  ]
  pair_choice = st.sidebar.selectbox(
      "Select Binary System", wilson_pairs, format_func=lambda x: x[0]
  )
  pair_name, c1, c2, lam12, lam21, v1_molar, v2_molar = pair_choice

  x1_wilson = st.sidebar.slider(
      f"Liquid Mole Fraction ({c1}) - x1",
      min_value=0.01,
      max_value=0.99,
      value=0.5,
      step=0.02,
  )
  T_wilson_c = st.sidebar.slider(
      "System Temperature (°C)", min_value=10.0, max_value=100.0, value=65.0, step=1.0
  )
  T_w_k = T_wilson_c + 273.15
  R_gas = 8.314

  st.subheader(f"Wilson Activity Coefficients: {pair_name}")
  st.write(
      "Computes liquid-phase activity coefficients ($\gamma_1, \gamma_2$), component"
      " partial pressures, and modified Raoult's law bubble pressures using the Wilson"
      " thermodynamic model."
  )

  try:
    Lambda12 = (v2_molar / v1_molar) * np.exp(-lam12 / (R_gas * T_w_k))
    Lambda21 = (v1_molar / v2_molar) * np.exp(-lam21 / (R_gas * T_w_k))

    def calc_wilson(x_1):
      x_2 = 1.0 - x_1
      x_1 = max(x_1, 1e-6)
      x_2 = max(x_2, 1e-6)

      term1 = -np.log(x_1 + Lambda12 * x_2) + x_2 * (
          Lambda12 / (x_1 + Lambda12 * x_2)
          - Lambda21 / (Lambda21 * x_1 + x_2)
      )
      term2 = -np.log(x_2 + Lambda21 * x_1) - x_1 * (
          Lambda12 / (x_1 + Lambda12 * x_2)
          - Lambda21 / (Lambda21 * x_1 + x_2)
      )

      gamma1 = np.exp(term1)
      gamma2 = np.exp(term2)
      return gamma1, gamma2

    g1, g2 = calc_wilson(x1_wilson)

    psat1 = CP.PropsSI("P", "T", T_w_k, "Q", 0, c1) / 100000.0
    psat2 = CP.PropsSI("P", "T", T_w_k, "Q", 0, c2) / 100000.0

    x2_wilson = 1.0 - x1_wilson
    p1_partial = x1_wilson * g1 * psat1
    p2_partial = x2_wilson * g2 * psat2
    p_bubble = p1_partial + p2_partial

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(f"Partial P ({c1})", f"{p1_partial:.3f} bar")
    col2.metric(f"Partial P ({c2})", f"{p2_partial:.3f} bar")
    col3.metric("Total Bubble P", f"{p_bubble:.3f} bar")
    col4.metric("Gamma 1", f"{g1:.4f}")
    col5.metric("Gamma 2", f"{g2:.4f}")

    st.markdown("---")
    st.subheader(
        "📈 Composition Sweep: Activity Coefficients & Partial Pressure P-x Behavior"
    )

    sweep_x = np.linspace(0.01, 0.99, 40)
    g1_list, g2_list, p1_part_list, p2_part_list, p_bub_list = [], [], [], [], []

    for xv in sweep_x:
      gw1, gw2 = calc_wilson(xv)
      p1_p = xv * gw1 * psat1
      p2_p = (1.0 - xv) * gw2 * psat2
      pb = p1_p + p2_p

      g1_list.append(gw1)
      g2_list.append(gw2)
      p1_part_list.append(p1_p)
      p2_part_list.append(p2_p)
      p_bub_list.append(pb)

    df_wilson = pd.DataFrame({
        f"Liquid Mole Fraction ({c1})": sweep_x,
        f"Gamma 1 ({c1})": g1_list,
        f"Gamma 2 ({c2})": g2_list,
        f"Partial Pressure {c1} (bar)": p1_part_list,
        f"Partial Pressure {c2} (bar)": p2_part_list,
        "Total Bubble Pressure (bar)": p_bub_list,
    })

    fig_w1 = px.line(
        df_wilson,
        x=f"Liquid Mole Fraction ({c1})",
        y=[f"Gamma 1 ({c1})", f"Gamma 2 ({c2})"],
        markers=True,
        title=f"Wilson Activity Coefficients vs Composition at {T_wilson_c}°C",
    )
    st.plotly_chart(fig_w1, use_container_width=True)

    fig_w2 = px.line(
        df_wilson,
        x=f"Liquid Mole Fraction ({c1})",
        y=[
            f"Partial Pressure {c1} (bar)",
            f"Partial Pressure {c2} (bar)",
            "Total Bubble Pressure (bar)",
        ],
        markers=True,
        title=f"Modified Raoult's Law Partial Pressures and P-x Curve for {pair_name} at {T_wilson_c}°C",
    )
    st.plotly_chart(fig_w2, use_container_width=True)

    st.download_button(
        label="📥 Download Wilson Model Data as CSV",
        data=df_wilson.to_csv(index=False).encode("utf-8"),
        file_name=f"{c1}_{c2}_wilson_activity.csv",
        mime="text/csv",
    )
  except Exception as e:
    st.error(f"Wilson model calculation error: {e}")

st.markdown("---")
st.markdown(
    "*Built with Python, CoolProp, and Streamlit as a commercial chemical"
    " engineering MVP.*"
)