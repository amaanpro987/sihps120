# Engineering Assumptions & Physical Formulations

## 1. Heavy Oil Viscosity & Rheology
- **Walther / ASTM D341 Equation**:
  $$\log_{10}(\log_{10}(\nu + 0.7)) = A - B \cdot \log_{10}(T_K)$$
  Calibrated with Baghewala crude dead oil viscosity:
  - $T = 40^\circ\text{C}$: $\mu = 12,500\text{ cP}$
  - $T = 200^\circ\text{C}$: $\mu = 45\text{ cP}$
- **Emulsion Viscosity**: Woelflin-Brinkman model for water-in-oil emulsions below inversion cut ($WC < 60\%$).

## 2. Cyclic Steam Stimulation (CSS) Thermal Reservoir
- **Steam Injection**: Marx-Langenheim heat balance determining heated radius $r_h(t)$ and overburden/underburden conduction losses.
- **Boberg-Lantz Analytical Cooling**:
  $$T_{avg}(t) = T_R + (T_{sat} - T_R) \cdot \frac{Q_{remaining}(t)}{Q_{initial}}$$
  Heat removal considers both convective produced fluid enthalpy and caprock Fourier conduction.
- **Thermal Inflow Performance Relationship (IPR)**:
  $$J_{thermal}(t) = \frac{0.00708 \cdot k \cdot h_{ft}}{\mu_{hot}(T_{avg}) \cdot B_o \cdot [\ln(r_h/r_w) + S]}$$

## 3. Annular Viscous Shear & Rod Floating
- **Couette Annular Downstroke Drag**:
  $$F_{drag} = \sum_{i} \frac{2\pi \cdot \mu_i \cdot v_{peak} \cdot \Delta L_i}{\ln(D_{tubing} / D_{rod})}$$
- **Rod Floating Criterion**:
  Floating occurs when $F_{drag} \ge W_{submerged}$.
  The digital twin enforces $F_{drag} / W_{submerged} \le 0.75$ for safe operation.

## 4. Modified Goodman Stress Analysis
- **Allowable Stress**:
  $$S_{allowable} = \left(\frac{T}{4} + 0.5625 \cdot S_{min}\right) \cdot SF$$
  where $SF = 0.90$ for heavy oil corrosive service, $T = 115,000\text{ psi}$ for API Grade D rods.
- **Goodman Loading %**:
  $$\text{Loading \%} = \frac{S_{max}}{S_{allowable}} \times 100\% \le 90\%$$

## 5. 1D Wave-Equation Dynamometer Card Synthesis
- Damped wave equation solved via Fourier series / Gibbs' method for surface and downhole cards across 6 operating modes:
  1. *Normal Full Fillage*
  2. *Heavy Crude Rod Float*
  3. *Fluid Pound*
  4. *Gas Interference*
  5. *Pump Unsetting / Valve Leak*
  6. *Unanchored Tubing Movement*
