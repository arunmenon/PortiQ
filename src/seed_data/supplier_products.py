"""
Supplier-product mappings for seed data.
~200 entries mapping 5 suppliers to products with realistic maritime procurement pricing.
"""

SUPPLIER_PRODUCTS = [
    # =========================================================================
    # OCEAN SHIP STORES (ocean-ship-stores, OSS) — ~45 products
    # PREMIUM tier, lead time 3-7 days
    # Specializes: Paints(23), Engine(61), Fasteners(71), Fittings(73),
    #              Lubricants(69), Chemicals(25), Deck(11)
    # =========================================================================

    # --- Paints (23) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230001",
        "supplier_sku": "OSS-230001",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 4,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "4100.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230002",
        "supplier_sku": "OSS-230002",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 4,
        "min_order_quantity": 2,
        "prices": [
            {"price": "5200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230003",
        "supplier_sku": "OSS-230003",
        "manufacturer": "Hempel",
        "brand": "Hempel Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "6200.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230005",
        "supplier_sku": "OSS-230005",
        "manufacturer": "Hempel",
        "brand": "Hempel Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "7500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230007",
        "supplier_sku": "OSS-230007",
        "manufacturer": "Chugoku",
        "brand": "Chugoku Marine",
        "lead_time_days": 6,
        "min_order_quantity": 2,
        "prices": [
            {"price": "8200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230010",
        "supplier_sku": "OSS-230010",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "2900.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230015",
        "supplier_sku": "OSS-230015",
        "manufacturer": "Chugoku",
        "brand": "Chugoku Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "12500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230020",
        "supplier_sku": "OSS-230020",
        "manufacturer": "Hempel",
        "brand": "Hempel Marine",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "14200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Engine Room Stores (61) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610001",
        "supplier_sku": "OSS-610001",
        "manufacturer": "Parker Hannifin",
        "brand": "Parker",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610003",
        "supplier_sku": "OSS-610003",
        "manufacturer": "Donaldson",
        "brand": "Donaldson",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "4000.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610005",
        "supplier_sku": "OSS-610005",
        "manufacturer": "Parker Hannifin",
        "brand": "Parker",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610010",
        "supplier_sku": "OSS-610010",
        "manufacturer": "Fleetguard",
        "brand": "Fleetguard",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610015",
        "supplier_sku": "OSS-610015",
        "manufacturer": "SKF",
        "brand": "SKF Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "8900.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610020",
        "supplier_sku": "OSS-610020",
        "manufacturer": "Donaldson",
        "brand": "Donaldson",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Fasteners (71) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710001",
        "supplier_sku": "OSS-710001",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 3,
        "min_order_quantity": 50,
        "prices": [
            {"price": "15.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "12.00", "currency": "INR", "min_quantity": 500, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710003",
        "supplier_sku": "OSS-710003",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 3,
        "min_order_quantity": 50,
        "prices": [
            {"price": "25.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "20.00", "currency": "INR", "min_quantity": 200, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710005",
        "supplier_sku": "OSS-710005",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 3,
        "min_order_quantity": 25,
        "prices": [
            {"price": "45.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710008",
        "supplier_sku": "OSS-710008",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 4,
        "min_order_quantity": 25,
        "prices": [
            {"price": "80.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710010",
        "supplier_sku": "OSS-710010",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 3,
        "min_order_quantity": 100,
        "prices": [
            {"price": "8.00", "currency": "INR", "min_quantity": 100, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "6.00", "currency": "INR", "min_quantity": 1000, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710015",
        "supplier_sku": "OSS-710015",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 4,
        "min_order_quantity": 10,
        "prices": [
            {"price": "120.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710020",
        "supplier_sku": "OSS-710020",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 3,
        "min_order_quantity": 50,
        "prices": [
            {"price": "35.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Fittings (73) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "730001",
        "supplier_sku": "OSS-730001",
        "manufacturer": "Generic",
        "brand": "MarinePipe",
        "lead_time_days": 5,
        "min_order_quantity": 5,
        "prices": [
            {"price": "350.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "730005",
        "supplier_sku": "OSS-730005",
        "manufacturer": "Generic",
        "brand": "MarinePipe",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "850.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "730010",
        "supplier_sku": "OSS-730010",
        "manufacturer": "Generic",
        "brand": "MarinePipe",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "730015",
        "supplier_sku": "OSS-730015",
        "manufacturer": "Generic",
        "brand": "MarinePipe",
        "lead_time_days": 5,
        "min_order_quantity": 5,
        "prices": [
            {"price": "480.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "730020",
        "supplier_sku": "OSS-730020",
        "manufacturer": "Generic",
        "brand": "MarinePipe",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Lubricants (69) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "690001",
        "supplier_sku": "OSS-690001",
        "manufacturer": "Shell",
        "brand": "Shell Marine",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "5500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "5000.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "690003",
        "supplier_sku": "OSS-690003",
        "manufacturer": "Shell",
        "brand": "Shell Marine",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "690005",
        "supplier_sku": "OSS-690005",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "7800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "690008",
        "supplier_sku": "OSS-690008",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "3200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "690010",
        "supplier_sku": "OSS-690010",
        "manufacturer": "Shell",
        "brand": "Shell Marine",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Chemicals (25) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "250001",
        "supplier_sku": "OSS-250001",
        "manufacturer": "Generic",
        "brand": "ChemMarine",
        "lead_time_days": 5,
        "min_order_quantity": 5,
        "prices": [
            {"price": "1200.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "250005",
        "supplier_sku": "OSS-250005",
        "manufacturer": "Generic",
        "brand": "ChemMarine",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2800.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "250010",
        "supplier_sku": "OSS-250010",
        "manufacturer": "Generic",
        "brand": "ChemMarine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Deck Stores (11) ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "110001",
        "supplier_sku": "OSS-110001",
        "manufacturer": "Generic",
        "brand": "DeckPro",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "110005",
        "supplier_sku": "OSS-110005",
        "manufacturer": "Generic",
        "brand": "DeckPro",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "110010",
        "supplier_sku": "OSS-110010",
        "manufacturer": "Generic",
        "brand": "DeckPro",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "750.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "110015",
        "supplier_sku": "OSS-110015",
        "manufacturer": "Generic",
        "brand": "DeckPro",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "110020",
        "supplier_sku": "OSS-110020",
        "manufacturer": "Generic",
        "brand": "DeckPro",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2600.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Gaskets (75) for OSS ---
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "750001",
        "supplier_sku": "OSS-750001",
        "manufacturer": "Klinger",
        "brand": "Klinger Marine",
        "lead_time_days": 5,
        "min_order_quantity": 5,
        "prices": [
            {"price": "450.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "750005",
        "supplier_sku": "OSS-750005",
        "manufacturer": "Klinger",
        "brand": "Klinger Marine",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "1200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "750010",
        "supplier_sku": "OSS-750010",
        "manufacturer": "Klinger",
        "brand": "Klinger Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "230025",
        "supplier_sku": "OSS-230025",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "9500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "610025",
        "supplier_sku": "OSS-610025",
        "manufacturer": "SKF",
        "brand": "SKF Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "5200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "ocean-ship-stores",
        "product_impa_code": "710025",
        "supplier_sku": "OSS-710025",
        "manufacturer": "Generic",
        "brand": "MarineFix",
        "lead_time_days": 3,
        "min_order_quantity": 25,
        "prices": [
            {"price": "180.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # =========================================================================
    # MARINE SUPPLIES INTERNATIONAL (marine-supplies-intl, MSI) — ~50 products
    # PREMIUM tier, lead time 3-7 days
    # Specializes: Deck(11), Mooring(15), Electrical Stores(31),
    #   Electrical Equip(33), Navigation(51), Communication(53), Pumps(65), Valves(87)
    # =========================================================================

    # --- Deck Stores (11) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "110002",
        "supplier_sku": "MSI-110002",
        "manufacturer": "Wichard",
        "brand": "Wichard Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "45.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "110003",
        "supplier_sku": "MSI-110003",
        "manufacturer": "Wichard",
        "brand": "Wichard Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "110008",
        "supplier_sku": "MSI-110008",
        "manufacturer": "Titan",
        "brand": "Titan Marine",
        "lead_time_days": 4,
        "min_order_quantity": 2,
        "prices": [
            {"price": "1500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "110012",
        "supplier_sku": "MSI-110012",
        "manufacturer": "Titan",
        "brand": "Titan Marine",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "35.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "110020",
        "supplier_sku": "MSI-110020",
        "manufacturer": "Wichard",
        "brand": "Wichard Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Mooring (15) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "150001",
        "supplier_sku": "MSI-150001",
        "manufacturer": "Generic",
        "brand": "MoorMaster",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "150003",
        "supplier_sku": "MSI-150003",
        "manufacturer": "Generic",
        "brand": "MoorMaster",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "75.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "150005",
        "supplier_sku": "MSI-150005",
        "manufacturer": "Generic",
        "brand": "MoorMaster",
        "lead_time_days": 6,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "150008",
        "supplier_sku": "MSI-150008",
        "manufacturer": "Generic",
        "brand": "MoorMaster",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "150010",
        "supplier_sku": "MSI-150010",
        "manufacturer": "Generic",
        "brand": "MoorMaster",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "120.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Electrical Stores (31) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310001",
        "supplier_sku": "MSI-310001",
        "manufacturer": "Philips",
        "brand": "Philips Marine",
        "lead_time_days": 4,
        "min_order_quantity": 10,
        "prices": [
            {"price": "85.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "70.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310003",
        "supplier_sku": "MSI-310003",
        "manufacturer": "Philips",
        "brand": "Philips Marine",
        "lead_time_days": 4,
        "min_order_quantity": 5,
        "prices": [
            {"price": "250.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310005",
        "supplier_sku": "MSI-310005",
        "manufacturer": "Osram",
        "brand": "Osram Marine",
        "lead_time_days": 5,
        "min_order_quantity": 5,
        "prices": [
            {"price": "180.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310008",
        "supplier_sku": "MSI-310008",
        "manufacturer": "Generic",
        "brand": "ElecMarine",
        "lead_time_days": 4,
        "min_order_quantity": 10,
        "prices": [
            {"price": "55.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310010",
        "supplier_sku": "MSI-310010",
        "manufacturer": "Osram",
        "brand": "Osram Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310015",
        "supplier_sku": "MSI-310015",
        "manufacturer": "Philips",
        "brand": "Philips Marine",
        "lead_time_days": 4,
        "min_order_quantity": 2,
        "prices": [
            {"price": "650.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310020",
        "supplier_sku": "MSI-310020",
        "manufacturer": "Generic",
        "brand": "ElecMarine",
        "lead_time_days": 5,
        "min_order_quantity": 5,
        "prices": [
            {"price": "2800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Electrical Equipment (33) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "330001",
        "supplier_sku": "MSI-330001",
        "manufacturer": "Schneider Electric",
        "brand": "Schneider",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "185.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "330003",
        "supplier_sku": "MSI-330003",
        "manufacturer": "Schneider Electric",
        "brand": "Schneider",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "330005",
        "supplier_sku": "MSI-330005",
        "manufacturer": "ABB",
        "brand": "ABB Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "12500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "330008",
        "supplier_sku": "MSI-330008",
        "manufacturer": "ABB",
        "brand": "ABB Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "250.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Navigation (51) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "510001",
        "supplier_sku": "MSI-510001",
        "manufacturer": "Furuno",
        "brand": "Furuno",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "42000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "510003",
        "supplier_sku": "MSI-510003",
        "manufacturer": "Furuno",
        "brand": "Furuno",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "550.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "510005",
        "supplier_sku": "MSI-510005",
        "manufacturer": "Garmin",
        "brand": "Garmin Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "28000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "510008",
        "supplier_sku": "MSI-510008",
        "manufacturer": "Garmin",
        "brand": "Garmin Marine",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Communication (53) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "530001",
        "supplier_sku": "MSI-530001",
        "manufacturer": "Icom",
        "brand": "Icom Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "18500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "530003",
        "supplier_sku": "MSI-530003",
        "manufacturer": "Icom",
        "brand": "Icom Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "350.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "530005",
        "supplier_sku": "MSI-530005",
        "manufacturer": "Sailor",
        "brand": "Sailor VSAT",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "48000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "530008",
        "supplier_sku": "MSI-530008",
        "manufacturer": "Sailor",
        "brand": "Sailor",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "12000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Pumps (65) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "650001",
        "supplier_sku": "MSI-650001",
        "manufacturer": "Grundfos",
        "brand": "Grundfos Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "450.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "650003",
        "supplier_sku": "MSI-650003",
        "manufacturer": "Grundfos",
        "brand": "Grundfos Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "32000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "650005",
        "supplier_sku": "MSI-650005",
        "manufacturer": "Generic",
        "brand": "PumpPro",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "18000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "650008",
        "supplier_sku": "MSI-650008",
        "manufacturer": "Generic",
        "brand": "PumpPro",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "5500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Valves (87) ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "870001",
        "supplier_sku": "MSI-870001",
        "manufacturer": "KSB",
        "brand": "KSB Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "870003",
        "supplier_sku": "MSI-870003",
        "manufacturer": "KSB",
        "brand": "KSB Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "12000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "870005",
        "supplier_sku": "MSI-870005",
        "manufacturer": "Generic",
        "brand": "ValveMaster",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "870008",
        "supplier_sku": "MSI-870008",
        "manufacturer": "Generic",
        "brand": "ValveMaster",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "870010",
        "supplier_sku": "MSI-870010",
        "manufacturer": "KSB",
        "brand": "KSB Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "15000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Electrical Stores (31) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "310025",
        "supplier_sku": "MSI-310025",
        "manufacturer": "Philips",
        "brand": "Philips Marine",
        "lead_time_days": 4,
        "min_order_quantity": 5,
        "prices": [
            {"price": "420.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Ropes (27) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "270001",
        "supplier_sku": "MSI-270001",
        "manufacturer": "Generic",
        "brand": "RopeMaster",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "85.00", "currency": "USD", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "270003",
        "supplier_sku": "MSI-270003",
        "manufacturer": "Generic",
        "brand": "RopeMaster",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "270005",
        "supplier_sku": "MSI-270005",
        "manufacturer": "Generic",
        "brand": "RopeMaster",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Gaskets (75) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "750001",
        "supplier_sku": "MSI-750001",
        "manufacturer": "Klinger",
        "brand": "Klinger Marine",
        "lead_time_days": 6,
        "min_order_quantity": 5,
        "prices": [
            {"price": "480.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "750005",
        "supplier_sku": "MSI-750005",
        "manufacturer": "Klinger",
        "brand": "Klinger Marine",
        "lead_time_days": 6,
        "min_order_quantity": 2,
        "prices": [
            {"price": "1350.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Navigation (51) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "510010",
        "supplier_sku": "MSI-510010",
        "manufacturer": "Furuno",
        "brand": "Furuno",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "15000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Communication (53) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "530010",
        "supplier_sku": "MSI-530010",
        "manufacturer": "Icom",
        "brand": "Icom Marine",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Pumps (65) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "650010",
        "supplier_sku": "MSI-650010",
        "manufacturer": "Grundfos",
        "brand": "Grundfos Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "22000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Mooring (15) for MSI ---
    {
        "supplier_org_slug": "marine-supplies-intl",
        "product_impa_code": "150012",
        "supplier_sku": "MSI-150012",
        "manufacturer": "Generic",
        "brand": "MoorMaster",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "5500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # =========================================================================
    # NAVKAR SHIP CHANDLERS (navkar-chandlers, NVK) — ~40 products
    # PREFERRED tier, lead time 3-10 days
    # Specializes: Deck(11), Cleaning(21), Paints(23), Galley(39),
    #              Provisions Fresh(45), Provisions Dry(47), Fasteners(71)
    # =========================================================================

    # --- Deck Stores (11) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "110001",
        "supplier_sku": "NVK-110001",
        "manufacturer": "Generic",
        "brand": "NavDeck",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1650.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "110003",
        "supplier_sku": "NVK-110003",
        "manufacturer": "Generic",
        "brand": "NavDeck",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2000.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "110010",
        "supplier_sku": "NVK-110010",
        "manufacturer": "Generic",
        "brand": "NavDeck",
        "lead_time_days": 4,
        "min_order_quantity": 5,
        "prices": [
            {"price": "680.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "110020",
        "supplier_sku": "NVK-110020",
        "manufacturer": "Generic",
        "brand": "NavDeck",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Cleaning (21) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210001",
        "supplier_sku": "NVK-210001",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 3,
        "min_order_quantity": 5,
        "prices": [
            {"price": "280.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "240.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210003",
        "supplier_sku": "NVK-210003",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 3,
        "min_order_quantity": 2,
        "prices": [
            {"price": "450.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210005",
        "supplier_sku": "NVK-210005",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210008",
        "supplier_sku": "NVK-210008",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 3,
        "min_order_quantity": 10,
        "prices": [
            {"price": "150.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210010",
        "supplier_sku": "NVK-210010",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 4,
        "min_order_quantity": 2,
        "prices": [
            {"price": "850.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210015",
        "supplier_sku": "NVK-210015",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 3,
        "min_order_quantity": 5,
        "prices": [
            {"price": "380.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Paints (23) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "230001",
        "supplier_sku": "NVK-230001",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 6,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "230002",
        "supplier_sku": "NVK-230002",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "5000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "230005",
        "supplier_sku": "NVK-230005",
        "manufacturer": "Generic",
        "brand": "NavPaint",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "3800.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "230010",
        "supplier_sku": "NVK-230010",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Galley (39) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "390001",
        "supplier_sku": "NVK-390001",
        "manufacturer": "Generic",
        "brand": "GalleyPro",
        "lead_time_days": 4,
        "min_order_quantity": 2,
        "prices": [
            {"price": "850.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "390003",
        "supplier_sku": "NVK-390003",
        "manufacturer": "Generic",
        "brand": "GalleyPro",
        "lead_time_days": 4,
        "min_order_quantity": 5,
        "prices": [
            {"price": "320.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "390005",
        "supplier_sku": "NVK-390005",
        "manufacturer": "Generic",
        "brand": "GalleyPro",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "390008",
        "supplier_sku": "NVK-390008",
        "manufacturer": "Generic",
        "brand": "GalleyPro",
        "lead_time_days": 3,
        "min_order_quantity": 10,
        "prices": [
            {"price": "180.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Fresh (45) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "450001",
        "supplier_sku": "NVK-450001",
        "manufacturer": "Generic",
        "brand": "FreshMarine",
        "lead_time_days": 3,
        "min_order_quantity": 10,
        "prices": [
            {"price": "120.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "450003",
        "supplier_sku": "NVK-450003",
        "manufacturer": "Generic",
        "brand": "FreshMarine",
        "lead_time_days": 3,
        "min_order_quantity": 5,
        "prices": [
            {"price": "250.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "450005",
        "supplier_sku": "NVK-450005",
        "manufacturer": "Generic",
        "brand": "FreshMarine",
        "lead_time_days": 3,
        "min_order_quantity": 20,
        "prices": [
            {"price": "80.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "450008",
        "supplier_sku": "NVK-450008",
        "manufacturer": "Generic",
        "brand": "FreshMarine",
        "lead_time_days": 3,
        "min_order_quantity": 10,
        "prices": [
            {"price": "350.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Dry (47) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "470001",
        "supplier_sku": "NVK-470001",
        "manufacturer": "Generic",
        "brand": "StorePro",
        "lead_time_days": 4,
        "min_order_quantity": 10,
        "prices": [
            {"price": "95.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "470003",
        "supplier_sku": "NVK-470003",
        "manufacturer": "Generic",
        "brand": "StorePro",
        "lead_time_days": 4,
        "min_order_quantity": 5,
        "prices": [
            {"price": "180.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "470005",
        "supplier_sku": "NVK-470005",
        "manufacturer": "Generic",
        "brand": "StorePro",
        "lead_time_days": 5,
        "min_order_quantity": 10,
        "prices": [
            {"price": "220.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "470008",
        "supplier_sku": "NVK-470008",
        "manufacturer": "Generic",
        "brand": "StorePro",
        "lead_time_days": 4,
        "min_order_quantity": 20,
        "prices": [
            {"price": "65.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Fasteners (71) ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "710001",
        "supplier_sku": "NVK-710001",
        "manufacturer": "Generic",
        "brand": "NavFix",
        "lead_time_days": 4,
        "min_order_quantity": 50,
        "prices": [
            {"price": "14.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "710005",
        "supplier_sku": "NVK-710005",
        "manufacturer": "Generic",
        "brand": "NavFix",
        "lead_time_days": 4,
        "min_order_quantity": 25,
        "prices": [
            {"price": "42.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "710010",
        "supplier_sku": "NVK-710010",
        "manufacturer": "Generic",
        "brand": "NavFix",
        "lead_time_days": 5,
        "min_order_quantity": 100,
        "prices": [
            {"price": "7.50", "currency": "INR", "min_quantity": 100, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "710015",
        "supplier_sku": "NVK-710015",
        "manufacturer": "Generic",
        "brand": "NavFix",
        "lead_time_days": 5,
        "min_order_quantity": 10,
        "prices": [
            {"price": "110.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "710020",
        "supplier_sku": "NVK-710020",
        "manufacturer": "Generic",
        "brand": "NavFix",
        "lead_time_days": 4,
        "min_order_quantity": 50,
        "prices": [
            {"price": "30.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Cleaning (21) for NVK ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210020",
        "supplier_sku": "NVK-210020",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 3,
        "min_order_quantity": 5,
        "prices": [
            {"price": "550.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "210025",
        "supplier_sku": "NVK-210025",
        "manufacturer": "Generic",
        "brand": "CleanShip",
        "lead_time_days": 4,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Galley (39) for NVK ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "390010",
        "supplier_sku": "NVK-390010",
        "manufacturer": "Generic",
        "brand": "GalleyPro",
        "lead_time_days": 5,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "390012",
        "supplier_sku": "NVK-390012",
        "manufacturer": "Generic",
        "brand": "GalleyPro",
        "lead_time_days": 4,
        "min_order_quantity": 5,
        "prices": [
            {"price": "680.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Fresh (45) additional for NVK ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "450010",
        "supplier_sku": "NVK-450010",
        "manufacturer": "Generic",
        "brand": "FreshMarine",
        "lead_time_days": 3,
        "min_order_quantity": 5,
        "prices": [
            {"price": "450.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Dry (47) additional for NVK ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "470010",
        "supplier_sku": "NVK-470010",
        "manufacturer": "Generic",
        "brand": "StorePro",
        "lead_time_days": 5,
        "min_order_quantity": 10,
        "prices": [
            {"price": "130.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Paints (23) additional for NVK ---
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "230015",
        "supplier_sku": "NVK-230015",
        "manufacturer": "Jotun",
        "brand": "Jotun Marine",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "11000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "navkar-chandlers",
        "product_impa_code": "230020",
        "supplier_sku": "NVK-230020",
        "manufacturer": "Generic",
        "brand": "NavPaint",
        "lead_time_days": 6,
        "min_order_quantity": 2,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # =========================================================================
    # SEAHAWK MARINE SUPPLIES (seahawk-marine, SHK) — ~35 products
    # VERIFIED tier, lead time 5-14 days
    # Specializes: Fire Fighting(17), Life Saving(19), Chemicals(25),
    #              Engine(61), Engine Equip(63), Hand Tools(77), Welding(79)
    # =========================================================================

    # --- Fire Fighting (17) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "170001",
        "supplier_sku": "SHK-170001",
        "manufacturer": "Generic",
        "brand": "FireGuard",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "170003",
        "supplier_sku": "SHK-170003",
        "manufacturer": "Generic",
        "brand": "FireGuard",
        "lead_time_days": 7,
        "min_order_quantity": 2,
        "prices": [
            {"price": "3200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "170005",
        "supplier_sku": "SHK-170005",
        "manufacturer": "Generic",
        "brand": "FireGuard",
        "lead_time_days": 8,
        "min_order_quantity": 1,
        "prices": [
            {"price": "15000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "170008",
        "supplier_sku": "SHK-170008",
        "manufacturer": "Generic",
        "brand": "FireGuard",
        "lead_time_days": 6,
        "min_order_quantity": 5,
        "prices": [
            {"price": "1800.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Life Saving (19) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "190001",
        "supplier_sku": "SHK-190001",
        "manufacturer": "Viking",
        "brand": "Viking Life-Saving",
        "lead_time_days": 8,
        "min_order_quantity": 1,
        "prices": [
            {"price": "45000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "190003",
        "supplier_sku": "SHK-190003",
        "manufacturer": "Viking",
        "brand": "Viking Life-Saving",
        "lead_time_days": 7,
        "min_order_quantity": 5,
        "prices": [
            {"price": "3500.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "190005",
        "supplier_sku": "SHK-190005",
        "manufacturer": "Viking",
        "brand": "Viking Life-Saving",
        "lead_time_days": 10,
        "min_order_quantity": 1,
        "prices": [
            {"price": "28000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "190008",
        "supplier_sku": "SHK-190008",
        "manufacturer": "Viking",
        "brand": "Viking Life-Saving",
        "lead_time_days": 7,
        "min_order_quantity": 10,
        "prices": [
            {"price": "1200.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "190010",
        "supplier_sku": "SHK-190010",
        "manufacturer": "Viking",
        "brand": "Viking Life-Saving",
        "lead_time_days": 8,
        "min_order_quantity": 2,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Chemicals (25) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "250001",
        "supplier_sku": "SHK-250001",
        "manufacturer": "Generic",
        "brand": "ChemSafe",
        "lead_time_days": 6,
        "min_order_quantity": 5,
        "prices": [
            {"price": "1100.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "250003",
        "supplier_sku": "SHK-250003",
        "manufacturer": "Generic",
        "brand": "ChemSafe",
        "lead_time_days": 7,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "250008",
        "supplier_sku": "SHK-250008",
        "manufacturer": "Generic",
        "brand": "ChemSafe",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Engine Room Stores (61) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "610001",
        "supplier_sku": "SHK-610001",
        "manufacturer": "Parker Hannifin",
        "brand": "Parker",
        "lead_time_days": 8,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2600.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "610005",
        "supplier_sku": "SHK-610005",
        "manufacturer": "Donaldson",
        "brand": "Donaldson",
        "lead_time_days": 7,
        "min_order_quantity": 2,
        "prices": [
            {"price": "3000.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "610010",
        "supplier_sku": "SHK-610010",
        "manufacturer": "Fleetguard",
        "brand": "Fleetguard",
        "lead_time_days": 8,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Engine Room Equipment (63) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "630001",
        "supplier_sku": "SHK-630001",
        "manufacturer": "SKF",
        "brand": "SKF Marine",
        "lead_time_days": 10,
        "min_order_quantity": 1,
        "prices": [
            {"price": "22000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "630003",
        "supplier_sku": "SHK-630003",
        "manufacturer": "SKF",
        "brand": "SKF Marine",
        "lead_time_days": 10,
        "min_order_quantity": 1,
        "prices": [
            {"price": "35000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "630005",
        "supplier_sku": "SHK-630005",
        "manufacturer": "Generic",
        "brand": "EnginePro",
        "lead_time_days": 8,
        "min_order_quantity": 1,
        "prices": [
            {"price": "15000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Hand Tools (77) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770001",
        "supplier_sku": "SHK-770001",
        "manufacturer": "Stanley",
        "brand": "Stanley",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770003",
        "supplier_sku": "SHK-770003",
        "manufacturer": "Stanley",
        "brand": "Stanley",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "1800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770005",
        "supplier_sku": "SHK-770005",
        "manufacturer": "Bahco",
        "brand": "Bahco",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770008",
        "supplier_sku": "SHK-770008",
        "manufacturer": "Bahco",
        "brand": "Bahco",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "4500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770010",
        "supplier_sku": "SHK-770010",
        "manufacturer": "Stanley",
        "brand": "Stanley",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770015",
        "supplier_sku": "SHK-770015",
        "manufacturer": "Stanley",
        "brand": "Stanley FatMax",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "12000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Welding (79) ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "790001",
        "supplier_sku": "SHK-790001",
        "manufacturer": "ESAB",
        "brand": "ESAB",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "5500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "790003",
        "supplier_sku": "SHK-790003",
        "manufacturer": "ESAB",
        "brand": "ESAB",
        "lead_time_days": 7,
        "min_order_quantity": 5,
        "prices": [
            {"price": "1200.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "1000.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "790005",
        "supplier_sku": "SHK-790005",
        "manufacturer": "ESAB",
        "brand": "ESAB",
        "lead_time_days": 8,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "790008",
        "supplier_sku": "SHK-790008",
        "manufacturer": "ESAB",
        "brand": "ESAB",
        "lead_time_days": 6,
        "min_order_quantity": 10,
        "prices": [
            {"price": "650.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "790010",
        "supplier_sku": "SHK-790010",
        "manufacturer": "ESAB",
        "brand": "ESAB Warrior",
        "lead_time_days": 10,
        "min_order_quantity": 1,
        "prices": [
            {"price": "14500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Fire Fighting (17) for SHK ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "170010",
        "supplier_sku": "SHK-170010",
        "manufacturer": "Generic",
        "brand": "FireGuard",
        "lead_time_days": 7,
        "min_order_quantity": 1,
        "prices": [
            {"price": "22000.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "170012",
        "supplier_sku": "SHK-170012",
        "manufacturer": "Generic",
        "brand": "FireGuard",
        "lead_time_days": 8,
        "min_order_quantity": 5,
        "prices": [
            {"price": "2500.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Chemicals (25) for SHK ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "250010",
        "supplier_sku": "SHK-250010",
        "manufacturer": "Generic",
        "brand": "ChemSafe",
        "lead_time_days": 7,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Hand Tools (77) for SHK ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770020",
        "supplier_sku": "SHK-770020",
        "manufacturer": "Bahco",
        "brand": "Bahco Professional",
        "lead_time_days": 6,
        "min_order_quantity": 1,
        "prices": [
            {"price": "6500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "770025",
        "supplier_sku": "SHK-770025",
        "manufacturer": "Stanley",
        "brand": "Stanley FatMax",
        "lead_time_days": 5,
        "min_order_quantity": 1,
        "prices": [
            {"price": "14500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Welding (79) additional for SHK ---
    {
        "supplier_org_slug": "seahawk-marine",
        "product_impa_code": "790012",
        "supplier_sku": "SHK-790012",
        "manufacturer": "ESAB",
        "brand": "ESAB",
        "lead_time_days": 7,
        "min_order_quantity": 2,
        "prices": [
            {"price": "8500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # =========================================================================
    # BHARAT SHIP STORES (bharat-ship-stores, BSS) — ~30 products
    # BASIC tier, lead time 7-21 days
    # Specializes: Deck(11), Paints(23), Provisions Fresh(45),
    #              Provisions Dry(47), Lubricants(69), Fasteners(71)
    # =========================================================================

    # --- Deck Stores (11) ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "110001",
        "supplier_sku": "BSS-110001",
        "manufacturer": "Generic",
        "brand": "BharatDeck",
        "lead_time_days": 10,
        "min_order_quantity": 2,
        "prices": [
            {"price": "1400.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "110005",
        "supplier_sku": "BSS-110005",
        "manufacturer": "Generic",
        "brand": "BharatDeck",
        "lead_time_days": 10,
        "min_order_quantity": 1,
        "prices": [
            {"price": "2800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "110010",
        "supplier_sku": "BSS-110010",
        "manufacturer": "Generic",
        "brand": "BharatDeck",
        "lead_time_days": 8,
        "min_order_quantity": 5,
        "prices": [
            {"price": "580.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "110015",
        "supplier_sku": "BSS-110015",
        "manufacturer": "Generic",
        "brand": "BharatDeck",
        "lead_time_days": 12,
        "min_order_quantity": 1,
        "prices": [
            {"price": "3500.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Paints (23) ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "230001",
        "supplier_sku": "BSS-230001",
        "manufacturer": "Asian Paints",
        "brand": "Asian Paints Marine",
        "lead_time_days": 8,
        "min_order_quantity": 5,
        "prices": [
            {"price": "3200.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "2800.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "230002",
        "supplier_sku": "BSS-230002",
        "manufacturer": "Asian Paints",
        "brand": "Asian Paints Marine",
        "lead_time_days": 8,
        "min_order_quantity": 2,
        "prices": [
            {"price": "3800.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "230005",
        "supplier_sku": "BSS-230005",
        "manufacturer": "Asian Paints",
        "brand": "Asian Paints Marine",
        "lead_time_days": 10,
        "min_order_quantity": 2,
        "prices": [
            {"price": "5500.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "230010",
        "supplier_sku": "BSS-230010",
        "manufacturer": "Asian Paints",
        "brand": "Asian Paints Marine",
        "lead_time_days": 8,
        "min_order_quantity": 5,
        "prices": [
            {"price": "2200.00", "currency": "INR", "min_quantity": 5, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "230015",
        "supplier_sku": "BSS-230015",
        "manufacturer": "Asian Paints",
        "brand": "Asian Paints Marine",
        "lead_time_days": 10,
        "min_order_quantity": 2,
        "prices": [
            {"price": "9800.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Fresh (45) ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "450001",
        "supplier_sku": "BSS-450001",
        "manufacturer": "Generic",
        "brand": "BharatFresh",
        "lead_time_days": 7,
        "min_order_quantity": 20,
        "prices": [
            {"price": "90.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "450003",
        "supplier_sku": "BSS-450003",
        "manufacturer": "Generic",
        "brand": "BharatFresh",
        "lead_time_days": 7,
        "min_order_quantity": 10,
        "prices": [
            {"price": "200.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "450005",
        "supplier_sku": "BSS-450005",
        "manufacturer": "Generic",
        "brand": "BharatFresh",
        "lead_time_days": 7,
        "min_order_quantity": 25,
        "prices": [
            {"price": "65.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Dry (47) ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "470001",
        "supplier_sku": "BSS-470001",
        "manufacturer": "Generic",
        "brand": "BharatStore",
        "lead_time_days": 8,
        "min_order_quantity": 20,
        "prices": [
            {"price": "75.00", "currency": "INR", "min_quantity": 20, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "470003",
        "supplier_sku": "BSS-470003",
        "manufacturer": "Generic",
        "brand": "BharatStore",
        "lead_time_days": 8,
        "min_order_quantity": 10,
        "prices": [
            {"price": "150.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "470005",
        "supplier_sku": "BSS-470005",
        "manufacturer": "Generic",
        "brand": "BharatStore",
        "lead_time_days": 9,
        "min_order_quantity": 10,
        "prices": [
            {"price": "185.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "470008",
        "supplier_sku": "BSS-470008",
        "manufacturer": "Generic",
        "brand": "BharatStore",
        "lead_time_days": 8,
        "min_order_quantity": 25,
        "prices": [
            {"price": "55.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Lubricants (69) ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "690001",
        "supplier_sku": "BSS-690001",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 10,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4800.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "690003",
        "supplier_sku": "BSS-690003",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 10,
        "min_order_quantity": 1,
        "prices": [
            {"price": "5800.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "690005",
        "supplier_sku": "BSS-690005",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 12,
        "min_order_quantity": 1,
        "prices": [
            {"price": "7200.00", "currency": "INR", "min_quantity": 1, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "690010",
        "supplier_sku": "BSS-690010",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 10,
        "min_order_quantity": 2,
        "prices": [
            {"price": "4200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Fasteners (71) ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710001",
        "supplier_sku": "BSS-710001",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 8,
        "min_order_quantity": 100,
        "prices": [
            {"price": "10.00", "currency": "INR", "min_quantity": 100, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
            {"price": "8.00", "currency": "INR", "min_quantity": 500, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710003",
        "supplier_sku": "BSS-710003",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 8,
        "min_order_quantity": 100,
        "prices": [
            {"price": "18.00", "currency": "INR", "min_quantity": 100, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710005",
        "supplier_sku": "BSS-710005",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 9,
        "min_order_quantity": 50,
        "prices": [
            {"price": "35.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710010",
        "supplier_sku": "BSS-710010",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 8,
        "min_order_quantity": 200,
        "prices": [
            {"price": "5.50", "currency": "INR", "min_quantity": 200, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710015",
        "supplier_sku": "BSS-710015",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 10,
        "min_order_quantity": 25,
        "prices": [
            {"price": "95.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710020",
        "supplier_sku": "BSS-710020",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 9,
        "min_order_quantity": 50,
        "prices": [
            {"price": "28.00", "currency": "INR", "min_quantity": 50, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "710025",
        "supplier_sku": "BSS-710025",
        "manufacturer": "Generic",
        "brand": "BharatFix",
        "lead_time_days": 10,
        "min_order_quantity": 25,
        "prices": [
            {"price": "150.00", "currency": "INR", "min_quantity": 25, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Additional Deck (11) for BSS ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "110020",
        "supplier_sku": "BSS-110020",
        "manufacturer": "Generic",
        "brand": "BharatDeck",
        "lead_time_days": 12,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2200.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Provisions Fresh (45) additional for BSS ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "450008",
        "supplier_sku": "BSS-450008",
        "manufacturer": "Generic",
        "brand": "BharatFresh",
        "lead_time_days": 7,
        "min_order_quantity": 10,
        "prices": [
            {"price": "280.00", "currency": "INR", "min_quantity": 10, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },

    # --- Lubricants (69) additional for BSS ---
    {
        "supplier_org_slug": "bharat-ship-stores",
        "product_impa_code": "690008",
        "supplier_sku": "BSS-690008",
        "manufacturer": "Castrol",
        "brand": "Castrol Marine",
        "lead_time_days": 10,
        "min_order_quantity": 2,
        "prices": [
            {"price": "2800.00", "currency": "INR", "min_quantity": 2, "valid_from": "2025-01-01", "valid_to": "2025-12-31"},
        ],
    },
]
