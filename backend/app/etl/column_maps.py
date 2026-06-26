"""Mapeamento canônico de colunas para cada fonte de dados."""

MTO_MAP = {
    "Area / Discipline":             "area_code",
    "ZONE":                          "zone",
    "Pipe Name":                     "line_tag",
    "3D Type":                       "item_3d_type",
    "Diâmetro 1 (pol.)":             "diameter_nom_in",
    "Diâmetro 2 (pol.)":             "diameter_sec_in",
    "Comprimento de Tubo (mm)":      "pipe_length_mm",
    "Descritivo":                    "description",
    "Especificação de Material":     "material_spec",
    "Código de Material Padrão":     "material_code_std",
    "Código de Material Alternativo":"material_code_alt",
    "Posição":                       "position",
    "Elevação (mm)":                 "elevation_mm",
    "Peso (kg)":                     "weight_kg",
    "Área Superfície Externa (mm2)": "surface_area_mm2",
    "Isométrico da Linha":           "isometrico",
    "Texto no Isométrico":           "isometric_text",
    "Spool Number":                  "spool_number_raw",
    "Escopo":                        "scope",
}

SGS_MAP = {
    "unid":                          "unit_code",
    "subunid":                       "sub_unit",
    "isometrico + - + spool":        "spool_key_raw",
    "fabricante":                    "manufacturer",
    "tp_linha":                      "line_type",
    "linha":                         "line_tag",
    "fluido":                        "fluid",
    "revisao":                       "revision",
    "mat":                           "material",
    "diametro":                      "diameter_mm",
    "dipol":                         "diameter_in",
    "esp":                           "thickness_mm",
    "hold":                          "hold",
    "espec":                         "spec",
    "comp":                          "length_m",
    "area":                          "area_m2",
    "peso":                          "weight_kg",
    "TIPO":                          "scope",
    "progfab":                       "pct_fab",
    "dtlibfab":                      "dt_lib_fab",
    "dtcort":                        "dt_corte",
    "ajudat":                        "dt_acoplamento",
    "soldat":                        "dt_soldagem",
    "vsdat":                         "dt_vs",
    "libdat":                        "dt_lib_end",
    "dtpint":                        "dt_pintura",
    "DTEMBARQUE":                    "dt_embarque",
    "dtlibmon":                      "dt_lib_mon",
    "PROGMON":                       "pct_mon",
    "dtprogmon":                     "dt_prog_mon",
    "dtpremon":                      "dt_pre_mon",
    "dtposmon":                      "dt_montagem",
    "sthdat":                        "dt_sth",
    "lavdat":                        "dt_lavagem",
    "sger":                          "sger",
    "sgermon":                       "sgermon",
    "tjs":                           "joints_total",
}

VALVES_MAP = {
    "ID":               "valve_id_raw",
    "ID+I":             "valve_tag",
    "Descrição do Item":"description",
    "DN":               "dn_mm",
    "Peso Unit":        "unit_weight_kg",
    "Qtd Prev":         "qty_planned",
    "Qtd Recebida":     "qty_received",
    "Peso Previsto":    "weight_planned_kg",
    "Peso Recebido":    "weight_received_kg",
    "DISPONIVEL":       "availability",
    "RESV QTY":         "qty_reserved",
    "ISSUE QTY":        "qty_issued",
}

JOINTS_EXCEL_MAP = {
    "UNID":             "unit_code",
    "subunid":          "sub_unit",
    "STH":              "sth",
    "isometrico":       "isometrico",
    "spool":            "spool",
    "junta":            "junta",
    "linha":            "line_tag",
    "espec":            "spec",
    "fluido":           "fluid",
    "P_C":              "pressure_class",
    "tipo":             "joint_type",
    "diam":             "diameter_mm",
    "POL":              "diameter_in",
    "esp":              "thickness_mm",
    "MAT":              "material",
    "NI":               "insp_level",
    "TT":               "requires_tt",
    "DU":               "requires_ut",
    "progfab":          "pct_fab",
    "dtcort":           "dt_corte",
    "dtaju":            "dt_acoplamento",
    "dtsold":           "dt_soldagem",
    "asraiz":           "welder_root_sin",
    "asench":           "welder_fill_sin",
    "corrida1":         "corrida_1",
    "corrida2":         "corrida_2",
    "corrida3":         "corrida_3",
    "corrida4":         "corrida_4",
    "dtVS":             "dt_vs",
    "RX_US":            "ndt_method",
    "dt_lib_END":       "dt_lib_end",
    "DTEMBARQUE":       "dt_embarque",
    "dtprogmon":        "dt_prog_mon",
    "dtpremon":         "dt_pre_mon",
    "dtposmon":         "dt_montagem",
    "HT_NUMBER1":       "heat_number_1",
    "HT_NUMBER2":       "heat_number_2",
    "sger":             "status_raw",
    "IEIS":             "ieis",
}

# Mapeamento sger fabricação → spool_status (SGS)
# spool_status enum: NAO_INICIADO, EM_FABRICACAO, FABRICADO, EM_CAMPO, MONTADO, TESTADO
SGER_TO_SPOOL_STATUS = {
    "02": "NAO_INICIADO",   # cancelado
    "03": "EM_CAMPO",       # spool de campo
    "05": "NAO_INICIADO",   # não alocado
    "06": "NAO_INICIADO",   # não iniciado
    "07": "EM_FABRICACAO",  # aguardando acoplamento
    "08": "EM_FABRICACAO",  # aguardando soldagem (variante)
    "09": "EM_FABRICACAO",  # aguardando VS fab
    "10": "EM_FABRICACAO",  # aguardando soldagem
    "11": "EM_FABRICACAO",  # em fabricação
    "12": "EM_FABRICACAO",  # aguardando LP/PM
    "13": "EM_FABRICACAO",  # aguardando liberação
    "14": "EM_FABRICACAO",  # aguardando liberação lote
    "15": "EM_FABRICACAO",  # aguardando RX/US
    "16": "EM_FABRICACAO",  # aguardando reparo
    "17": "EM_FABRICACAO",  # aguardando ferrita
    "18": "EM_FABRICACAO",  # aguardando medição ferrita
    "19": "EM_FABRICACAO",  # aguardando TT
    "20": "EM_FABRICACAO",  # em processo
    "21": "EM_FABRICACAO",  # aguardando PWHT
    "22": "EM_FABRICACAO",  # aguardando inspeção
    "23": "EM_FABRICACAO",  # aguardando cadastro
    "24": "EM_FABRICACAO",  # aguardando dimensionamento
    "25": "EM_FABRICACAO",  # aguardando suporte
    "26": "EM_FABRICACAO",  # aguardando rastreabilidade
    "27": "EM_FABRICACAO",  # aguardando LM
    "28": "EM_FABRICACAO",  # aguardando liga
    "29": "EM_FABRICACAO",  # aguardando cola
    "30": "EM_FABRICACAO",  # aguardando pintura
    "31": "EM_FABRICACAO",  # aguardando dimensional
    "32": "EM_FABRICACAO",  # aguardando jato
    "33": "EM_FABRICACAO",  # aguardando jato/pintura (FAB)
    "34": "EM_FABRICACAO",  # aguardando jato/pintura fundo
    "35": "EM_FABRICACAO",  # aguardando acabamento
    "36": "FABRICADO",      # liberado para expedição / não iniciada montagem
    "37": "FABRICADO",      # liberado para montagem
    "38": "FABRICADO",      # aguardando cadastro LM
    "39": "EM_CAMPO",       # aguardando recebimento liga (campo)
    "40": "EM_CAMPO",       # aguardando soldagem campo
    "41": "EM_CAMPO",       # em campo
    "42": "EM_CAMPO",       # aguardando acoplamento campo
    "43": "EM_CAMPO",       # aguardando VS campo
    "44": "EM_CAMPO",       # aguardando RX campo
    "45": "EM_CAMPO",       # aguardando VS campo
    "46": "EM_CAMPO",       # aguardando TT campo
    "47": "EM_CAMPO",       # aguardando RX/US campo
    "48": "EM_CAMPO",       # aguardando LP/PM campo
    "49": "EM_CAMPO",       # aguardando lib ROS/cola
    "50": "MONTADO",        # montado
    "51": "MONTADO",        # montagem concluída
    "52": "MONTADO",        # aguardando RX/US montagem
    "53": "MONTADO",        # aguardando LP
    "54": "MONTADO",        # aguardando inspeção final
    "55": "MONTADO",        # aguardando hidroteste
    "56": "MONTADO",        # aguardando liberação final
    "57": "MONTADO",        # aguardando suporte campo
    "58": "MONTADO",        # aguardando dimensional campo
    "59": "MONTADO",        # aguardando lib junta suporte
    "60": "MONTADO",        # aguardando rastreabilidade campo
    "61": "MONTADO",        # aguardando dimensional campo
    "62": "MONTADO",        # aguardando pintura campo
    "63": "MONTADO",        # aguardando suporte
    "64": "TESTADO",        # testado
    "65": "TESTADO",        # hidroteste concluído
    "66": "TESTADO",        # liberado final
}

# Mapeamento dos códigos sger → enum joint_status
SGER_TO_STATUS = {
    "01": "01_NAO_INICIADA",
    "03": "03_AGUARD_ACOPLAMENTO",
    "04": "04_AGUARD_SOLDAGEM",
    "09": "09_AGUARD_VS",
    "12": "12_AGUARD_LP_PM",
    "14": "14_AGUARD_LIB_LOTE",
    "15": "15_AGUARD_RX_US",
    "18": "18_AGUARD_RX_REPARO",
    "23": "23_AGUARD_TT",
    "30": "30_LIBERADA",
}
