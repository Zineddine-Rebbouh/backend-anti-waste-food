-- Adds one extra active listing without deleting or updating existing data.
-- Run with:
--   Get-Content -Raw scripts/add_active_listing_seed.sql | docker exec -i savefood_db psql -U savefood_user -d savefood_db -v ON_ERROR_STOP=1

DO $$
DECLARE
    merchant_uuid uuid;
    category_pk bigint;
    listing_uuid uuid := 'e315e576-3f1d-4f09-bb3d-9b3a55e82017';
BEGIN
    SELECT id
    INTO merchant_uuid
    FROM users_user
    WHERE email IN ('zinedinerabouh@gmail.com', 'zinedinerabotuh@gmail.com')
      AND user_type = 'merchant'
    ORDER BY CASE email
        WHEN 'zinedinerabouh@gmail.com' THEN 1
        WHEN 'zinedinerabotuh@gmail.com' THEN 2
        ELSE 3
    END
    LIMIT 1;

    IF merchant_uuid IS NULL THEN
        RAISE EXCEPTION 'No matching merchant user found for active listing seed.';
    END IF;

    SELECT id
    INTO category_pk
    FROM listings_category
    WHERE slug = 'restaurant'
    LIMIT 1;

    IF category_pk IS NULL THEN
        RAISE EXCEPTION 'No restaurant category found for active listing seed.';
    END IF;

    INSERT INTO listings_listing (
        created_at,
        updated_at,
        id,
        merchant_id,
        category_id,
        title,
        title_ar,
        title_fr,
        description,
        description_ar,
        description_fr,
        original_price,
        discounted_price,
        currency,
        quantity_total,
        quantity_available,
        unit,
        freshness_grade,
        status,
        pickup_start,
        pickup_end,
        is_donation,
        allergens,
        dietary_flags,
        search_vector,
        view_count,
        trending_score
    )
    VALUES (
        now(),
        now(),
        listing_uuid,
        merchant_uuid,
        category_pk,
        'Chicken Couscous Lunch Box',
        '',
        'Box Dejeuner Couscous Poulet',
        'Fresh surplus couscous lunch boxes with chicken and vegetables, packed today and ready for pickup.',
        '',
        'Boxes de couscous au poulet et legumes, preparees aujourd hui et disponibles au retrait.',
        1200.00,
        550.00,
        'DZD',
        8,
        8,
        'box',
        'A',
        'active',
        now() + interval '30 minutes',
        now() + interval '8 hours',
        false,
        '["gluten"]'::jsonb,
        '{"is_halal": true, "is_vegetarian": false, "is_vegan": false}'::jsonb,
        NULL,
        0,
        0.0
    )
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO listings_listingphoto (
        photo_url,
        is_primary,
        "order",
        listing_id
    )
    SELECT
        'https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=800&q=80',
        true,
        1,
        listing_uuid
    WHERE EXISTS (
        SELECT 1
        FROM listings_listing
        WHERE id = listing_uuid
    )
    AND NOT EXISTS (
        SELECT 1
        FROM listings_listingphoto
        WHERE listing_id = listing_uuid
          AND is_primary = true
    );

RAISE NOTICE 'Active listing seed ensured: %', listing_uuid;
END $$;

DO $$
DECLARE
    merchant_uuid uuid;
    category_pk bigint;
    listing_uuid uuid := '0d6cb07f-3e18-4b7a-a0c2-4e1c2d2c8e91';
BEGIN
    SELECT id
    INTO merchant_uuid
    FROM users_user
    WHERE email IN ('zinedinerabouh@gmail.com', 'zinedinerabotuh@gmail.com')
      AND user_type = 'merchant'
    ORDER BY CASE email
        WHEN 'zinedinerabouh@gmail.com' THEN 1
        WHEN 'zinedinerabotuh@gmail.com' THEN 2
        ELSE 3
    END
    LIMIT 1;

    IF merchant_uuid IS NULL THEN
        RAISE EXCEPTION 'No matching merchant user found for second active listing seed.';
    END IF;

    SELECT id
    INTO category_pk
    FROM listings_category
    WHERE slug = 'bakery'
    LIMIT 1;

    IF category_pk IS NULL THEN
        SELECT id
        INTO category_pk
        FROM listings_category
        WHERE slug = 'restaurant'
        LIMIT 1;
    END IF;

    IF category_pk IS NULL THEN
        RAISE EXCEPTION 'No bakery or restaurant category found for second active listing seed.';
    END IF;

    INSERT INTO listings_listing (
        created_at,
        updated_at,
        id,
        merchant_id,
        category_id,
        title,
        title_ar,
        title_fr,
        description,
        description_ar,
        description_fr,
        original_price,
        discounted_price,
        currency,
        quantity_total,
        quantity_available,
        unit,
        freshness_grade,
        status,
        pickup_start,
        pickup_end,
        is_donation,
        allergens,
        dietary_flags,
        search_vector,
        view_count,
        trending_score
    )
    VALUES (
        now(),
        now(),
        listing_uuid,
        merchant_uuid,
        category_pk,
        'Fresh Croissant & Tart Box',
        '',
        'Boite de croissants et tartes fraiches',
        'A mixed box of fresh croissants, fruit tarts, and brioche from today''s closing batch, packed for same-day pickup.',
        '',
        'Un assortiment de croissants, tartes aux fruits et brioches de la fournee du jour, prepare pour retrait le jour meme.',
        980.00,
        450.00,
        'DZD',
        12,
        12,
        'box',
        'A',
        'active',
        now() + interval '45 minutes',
        now() + interval '6 hours',
        false,
        '["gluten", "dairy", "eggs"]'::jsonb,
        '{"is_halal": true, "is_vegetarian": true, "is_vegan": false}'::jsonb,
        NULL,
        0,
        0.0
    )
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO listings_listingphoto (
        photo_url,
        is_primary,
        "order",
        listing_id
    )
    SELECT
        'https://images.unsplash.com/photo-1483695028939-5bb13f8648b0?w=800&q=80',
        true,
        1,
        listing_uuid
    WHERE EXISTS (
        SELECT 1
        FROM listings_listing
        WHERE id = listing_uuid
    )
    AND NOT EXISTS (
        SELECT 1
        FROM listings_listingphoto
        WHERE listing_id = listing_uuid
          AND is_primary = true
    );

    RAISE NOTICE 'Second active listing seed ensured: %', listing_uuid;
END $$;
