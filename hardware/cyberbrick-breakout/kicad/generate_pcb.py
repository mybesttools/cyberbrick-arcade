#!/usr/bin/env python3
"""
generate_pcb.py — CyberBrick Breakout Board PCB layout generator
Writes a valid KiCad 7/8 .kicad_pcb file without requiring pcbnew.

Board: ~85 x 70 mm
  - ABrobot ESP32-C3 OLED socket (U1): 2x 1x8 female headers, centred top-half
  - J1-J4: SH1.0 3-pin joystick connectors, top edge
  - J9-J24: SH1.0 2-pin button connectors, bottom edge (2 rows of 8)
  - J6: MCP23017 2x9 button header, right edge
  - J7: I2C 1x4 header, right edge
  - J8: Power 1x2 header, right edge
  - C1-C4: 0402 decoupling caps near joystick connectors
  - 4x M3 mounting holes
"""

BOARD_W = 85.0
BOARD_H = 70.0

# KiCad layer IDs
F_CU   = "F.Cu"
B_CU   = "B.Cu"
F_SilkS = "F.SilkS"
B_SilkS = "B.SilkS"
F_Fab  = "F.Fab"
Edge_Cuts = "Edge.Cuts"
F_Courtyard = "F.Courtyard"
B_Courtyard = "B.Courtyard"
F_Paste = "F.Paste"
B_Paste = "B.Paste"
F_Mask = "F.Mask"
B_Mask = "B.Mask"

net_names = [
    "GND", "VCC",
    "ADC_LX", "ADC_LY", "ADC_RX", "ADC_RY",
    "I2C_SDA", "I2C_SCL",
    "BTN_DL_UP", "BTN_DL_LEFT", "BTN_DL_RIGHT", "BTN_DL_DOWN",
    "BTN_DR_UP", "BTN_DR_LEFT", "BTN_DR_RIGHT", "BTN_DR_DOWN",
    "BTN_SHL1", "BTN_SHL2", "BTN_SHR1", "BTN_SHR2",
    "BTN_START", "BTN_SELECT", "BTN_HOTKEY", "BTN_COIN",
]
net_idx = {n: i+1 for i, n in enumerate(net_names)}

def net(name):
    return net_idx.get(name, 0)

lines = []

def emit(s):
    lines.append(s)

def header():
    emit('(kicad_pcb (version 20231120) (generator "cyberbrick-gen")')
    emit('  (general (thickness 1.6) (legacy_teardrops no))')
    emit('  (paper "A4")')
    emit('  (title_block')
    emit('    (title "CyberBrick Controller Breakout")')
    emit('    (rev "1.2")')
    emit('    (company "DIY")')
    emit('  )')
    emit('  (layers')
    for spec in [
        '(0 "F.Cu" signal)', '(31 "B.Cu" signal)',
        '(32 "B.Adhes" user "B.Adhesive")', '(33 "F.Adhes" user "F.Adhesive")',
        '(34 "B.Paste" user)', '(35 "F.Paste" user)',
        '(36 "B.SilkS" user "B.Silkscreen")', '(37 "F.SilkS" user "F.Silkscreen")',
        '(38 "B.Mask" user)', '(39 "F.Mask" user)',
        '(40 "Dwgs.User" user "User.Drawings")',
        '(44 "Edge.Cuts" user)',
        '(49 "F.Courtyard" user)', '(50 "B.Courtyard" user)',
        '(51 "F.Fab" user)', '(52 "B.Fab" user)',
    ]:
        emit(f'    {spec}')
    emit('  )')
    # nets
    emit('  (net 0 "")')
    for name, idx in net_idx.items():
        emit(f'  (net {idx} "{name}")')

def edge_cuts():
    # Board outline rectangle
    emit(f'  (gr_rect (start 0 0) (end {BOARD_W} {BOARD_H})')
    emit(f'    (stroke (width 0.05) (type solid)) (layer "Edge.Cuts"))')

def mounting_holes():
    # M3 holes 3mm from corners
    for x, y, ref in [
        (3.5, 3.5, "H1"), (BOARD_W-3.5, 3.5, "H2"),
        (3.5, BOARD_H-3.5, "H3"), (BOARD_W-3.5, BOARD_H-3.5, "H4"),
    ]:
        emit(f'  (footprint "MountingHole:MountingHole_3.2mm_M3" (layer "F.Cu") (at {x} {y})')
        emit(f'    (reference "{ref}" (at 0 -4) (layer "F.SilkS") (hide yes))')
        emit(f'    (value "M3" (at 0 4) (layer "F.Fab") (hide yes))')
        emit(f'    (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))')
        emit('  )')

def smd_pad(pad_num, net_name, x, y, w=1.0, h=1.5, layer="F.Cu"):
    n = net(net_name)
    emit(f'    (pad "{pad_num}" smd rect (at {x} {y}) (size {w} {h})')
    emit(f'      (layers "{layer}" "F.Paste" "F.Mask") (net {n} "{net_name}"))')

def thru_pad(pad_num, net_name, x, y, drill=0.8, size=1.6):
    n = net(net_name)
    emit(f'    (pad "{pad_num}" thru_hole circle (at {x} {y}) (size {size} {size})')
    emit(f'      (drill {drill}) (layers "*.Cu" "*.Mask") (net {n} "{net_name}"))')

def silkscreen_text(text, x, y, size=1.0):
    emit(f'  (gr_text "{text}" (at {x} {y}) (layer "F.SilkS")')
    emit(f'    (effects (font (size {size} {size}) (thickness 0.15))))')

def ref_value(ref, value, rx, ry, vx, vy):
    emit(f'    (reference "{ref}" (at {rx} {ry}) (layer "F.SilkS"))')
    emit(f'    (value "{value}" (at {vx} {vy}) (layer "F.Fab") (hide yes))')

# ─── SH1.0 3-pin RA SMD footprint (SM03B-SRSS-TB) ──────────────────────────
# 3 pads at 1.0mm pitch, SMD, horizontal (connector faces board edge)
# Pad size ~1.55 x 1.8mm, MP pad on right
def sh10_3pin(ref, label, cx, cy, nets3):
    """nets3 = [net_pin1, net_pin2, net_pin3]  (VCC, SIG, GND)"""
    emit(f'  (footprint "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal"')
    emit(f'    (layer "F.Cu") (at {cx} {cy})')
    ref_value(ref, label, 0, -3.5, 0, 3.5)
    # 3 signal pads
    for i, (offset, net_name) in enumerate(zip([-1.0, 0.0, 1.0], nets3)):
        smd_pad(str(i+1), net_name, offset, 0, w=0.95, h=1.55)
    # MP (mounting) pad
    emit(f'    (pad "MP" smd rect (at 2.25 0) (size 1.2 2.0)')
    emit(f'      (layers "F.Cu" "F.Paste" "F.Mask") (net 0 ""))')
    emit('  )')

# ─── SH1.0 2-pin RA SMD footprint (SM02B-SRSS-TB) ──────────────────────────
def sh10_2pin(ref, label, cx, cy, net1, net2="GND"):
    emit(f'  (footprint "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal"')
    emit(f'    (layer "F.Cu") (at {cx} {cy})')
    ref_value(ref, label, 0, -3.0, 0, 3.0)
    smd_pad("1", net1,  -0.5, 0, w=0.95, h=1.55)
    smd_pad("2", net2,   0.5, 0, w=0.95, h=1.55)
    emit(f'    (pad "MP" smd rect (at 1.75 0) (size 1.2 2.0)')
    emit(f'      (layers "F.Cu" "F.Paste" "F.Mask") (net 0 ""))')
    emit('  )')

# ─── 0402 capacitor ──────────────────────────────────────────────────────────
def cap_0402(ref, cx, cy, net_p="VCC", net_n="GND"):
    emit(f'  (footprint "Capacitor_SMD:C_0402_1005Metric" (layer "F.Cu") (at {cx} {cy})')
    ref_value(ref, "100nF", 0, -1.5, 0, 1.5)
    smd_pad("1", net_p, -0.5, 0, w=0.5, h=0.5)
    smd_pad("2", net_n,  0.5, 0, w=0.5, h=0.5)
    emit('  )')

# ─── 2.54mm pin header (male, vertical, through-hole) ────────────────────────
def header_1xN(ref, label, x0, y0, n_pins, net_list, pitch=2.54):
    emit(f'  (footprint "Connector_PinHeader_2.54mm:PinHeader_1x{n_pins:02d}_P2.54mm_Vertical"')
    emit(f'    (layer "F.Cu") (at {x0} {y0})')
    ref_value(ref, label, 0, -3, 0, 3)
    for i, net_name in enumerate(net_list):
        py = i * pitch
        thru_pad(str(i+1), net_name, 0, py)
    emit('  )')

def header_2xN(ref, label, x0, y0, n_pairs, net_list, pitch=2.54):
    """2-row header. net_list alternates odd/even rows."""
    emit(f'  (footprint "Connector_PinHeader_2.54mm:PinHeader_2x{n_pairs:02d}_P2.54mm_Vertical"')
    emit(f'    (layer "F.Cu") (at {x0} {y0})')
    ref_value(ref, label, 0, -3, 0, 3)
    for i, net_name in enumerate(net_list):
        col = i % 2          # 0=left col, 1=right col
        row = i // 2
        px = col * pitch
        py = row * pitch
        thru_pad(str(i+1), net_name, px, py)
    emit('  )')

# ─── ESP32-C3 socket (2× 1x8 female, 2.54mm) ─────────────────────────────────
# Module is ~25×20mm. Two rows of 8 pins, 15.24mm (600mil) apart.
# We place the sockets so module sits centred on the board.
# Socket origin = pin 1 of each row.
ESP32_CX = 35.0   # centre X of module
ESP32_CY = 25.0   # centre Y of module
ROW_SEP  = 15.24  # row-to-row spacing (600mil) — measure before ordering!

def esp32_socket():
    # Top row: pins T1-T8 (left to right)
    # nets: NC NC NC NC I2C_SCL I2C_SDA NC ADC_RY
    top_nets = ["", "", "", "", "I2C_SCL", "I2C_SDA", "", "ADC_RY"]
    rx = ESP32_CX - 3.5 * 2.54   # pin 1 at left
    ry = ESP32_CY - ROW_SEP / 2
    emit(f'  (footprint "Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical"')
    emit(f'    (layer "F.Cu") (at {rx} {ry})')
    ref_value("U1A", "ESP32-C3 top row", 0, -3, 0, 3)
    for i, net_name in enumerate(top_nets):
        px = i * 2.54
        if net_name:
            thru_pad(str(i+1), net_name, px, 0)
        else:
            emit(f'    (pad "{i+1}" thru_hole circle (at {px} 0) (size 1.6 1.6)')
            emit(f'      (drill 0.8) (layers "*.Cu" "*.Mask") (net 0 ""))')
    emit('  )')

    # Bottom row: pins B1-B8
    # nets: NC GND VCC NC NC ADC_RX ADC_LY ADC_LX
    bot_nets = ["", "GND", "VCC", "", "", "ADC_RX", "ADC_LY", "ADC_LX"]
    bx = ESP32_CX - 3.5 * 2.54
    by = ESP32_CY + ROW_SEP / 2
    emit(f'  (footprint "Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical"')
    emit(f'    (layer "F.Cu") (at {bx} {by})')
    ref_value("U1B", "ESP32-C3 bot row", 0, -3, 0, 3)
    for i, net_name in enumerate(bot_nets):
        px = i * 2.54
        if net_name:
            thru_pad(str(i+1), net_name, px, 0)
        else:
            emit(f'    (pad "{i+1}" thru_hole circle (at {px} 0) (size 1.6 1.6)')
            emit(f'      (drill 0.8) (layers "*.Cu" "*.Mask") (net 0 ""))')
    emit('  )')

def joystick_connectors():
    # J1-J4 along top edge at y=4, spread across top
    # VCC=pin1, SIG=pin2, GND=pin3
    configs = [
        ("J1", "LX", "ADC_LX"),
        ("J2", "LY", "ADC_LY"),
        ("J3", "RX", "ADC_RX"),
        ("J4", "RY", "ADC_RY"),
    ]
    xs = [12.0, 24.0, 36.0, 48.0]
    for (ref, label, sig_net), x in zip(configs, xs):
        sh10_3pin(ref, label, x, 4.0, ["VCC", sig_net, "GND"])

    # 0402 decoupling caps just below connectors
    for i, (x, ref) in enumerate(zip(xs, ["C1","C2","C3","C4"])):
        cap_0402(ref, x, 9.0)

def button_connectors():
    # J9-J16 (d-pad left + right): bottom edge row 1 at y=63
    # J17-J24 (shoulders + function): bottom edge row 2 at y=67
    btn_configs = [
        # (ref,  label,          net)
        ("J9",  "DL_UP",   "BTN_DL_UP"),
        ("J10", "DL_LEFT", "BTN_DL_LEFT"),
        ("J11", "DL_RIGHT","BTN_DL_RIGHT"),
        ("J12", "DL_DOWN", "BTN_DL_DOWN"),
        ("J13", "DR_UP",   "BTN_DR_UP"),
        ("J14", "DR_LEFT", "BTN_DR_LEFT"),
        ("J15", "DR_RIGHT","BTN_DR_RIGHT"),
        ("J16", "DR_DOWN", "BTN_DR_DOWN"),
        ("J17", "SHL1",    "BTN_SHL1"),
        ("J18", "SHL2",    "BTN_SHL2"),
        ("J19", "SHR1",    "BTN_SHR1"),
        ("J20", "SHR2",    "BTN_SHR2"),
        ("J21", "START",   "BTN_START"),
        ("J22", "SELECT",  "BTN_SELECT"),
        ("J23", "HOTKEY",  "BTN_HOTKEY"),
        ("J24", "COIN",    "BTN_COIN"),
    ]
    pitch = 5.0
    for i, (ref, label, btn_net) in enumerate(btn_configs):
        row = i // 8
        col = i % 8
        x = 5.0 + col * pitch
        y = BOARD_H - 7.0 + row * 4.0
        sh10_2pin(ref, label, x, y, btn_net, "GND")

def output_headers():
    # J6: MCP23017 2x9 button header — right side
    mcp_nets = [
        "BTN_DL_UP",   "BTN_DR_UP",
        "BTN_DL_LEFT", "BTN_DR_LEFT",
        "BTN_DL_RIGHT","BTN_DR_RIGHT",
        "BTN_DL_DOWN", "BTN_DR_DOWN",
        "BTN_SHL1",    "BTN_SHR1",
        "BTN_SHL2",    "BTN_SHR2",
        "BTN_START",   "BTN_SELECT",
        "BTN_HOTKEY",  "BTN_COIN",
        "GND",         "GND",
    ]
    header_2xN("J6", "MCP_BTNS", 79.0, 15.0, 9, mcp_nets)

    # J7: I2C 1x4
    header_1xN("J7", "I2C", 79.0, 43.0, 4, ["I2C_SDA","I2C_SCL","VCC","GND"])

    # J8: Power 1x2
    header_1xN("J8", "PWR_IN", 79.0, 55.0, 2, ["VCC","GND"])

def traces_and_zones():
    # GND pour on B.Cu
    emit(f'  (zone (net {net("GND")}) (net_name "GND") (layer "B.Cu") (hatch edge 0.508)')
    emit(f'    (connect_pads (clearance 0.2))')
    emit(f'    (min_thickness 0.25)')
    emit(f'    (fill yes (mode solid) (thermal_gap 0.3) (thermal_bridge_width 0.3))')
    emit(f'    (polygon (pts')
    emit(f'      (xy 0.5 0.5) (xy {BOARD_W-0.5} 0.5)')
    emit(f'      (xy {BOARD_W-0.5} {BOARD_H-0.5}) (xy 0.5 {BOARD_H-0.5})')
    emit(f'    ))')
    emit('  )')

def silkscreen_labels():
    silkscreen_text("CyberBrick Breakout v1.2", BOARD_W/2, BOARD_H/2, size=1.2)
    silkscreen_text("GPIO2=BOOT STRAP - no pulldown!", 42, 48, size=0.6)

def footer():
    emit(')')

# ── Generate ─────────────────────────────────────────────────────────────────

header()
edge_cuts()
mounting_holes()
esp32_socket()
joystick_connectors()
button_connectors()
output_headers()
traces_and_zones()
silkscreen_labels()
footer()

out = "\n".join(lines)
with open("/tmp/esp32-c3-arcade/hardware/cyberbrick-breakout/kicad/cyberbrick-breakout.kicad_pcb", "w") as f:
    f.write(out)

print(f"Written {len(out)} bytes")
print(f"Total footprints placed: ESP32-C3(2) + J1-J4(4) + J9-J24(16) + J6+J7+J8(3) + C1-C4(4) + H1-H4(4) = 33")
