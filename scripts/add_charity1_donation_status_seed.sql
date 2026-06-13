-- Adds active and completed donation examples for charity1@tawfir.dz.
-- Existing rows are not deleted. Fixed UUIDs make this safe to rerun.
-- Run with:
--   Get-Content -Raw scripts/add_charity1_donation_status_seed.sql | docker exec -i savefood_db psql -U savefood_user -d savefood_db -v ON_ERROR_STOP=1

DO $$
DECLARE
    charity_uuid uuid;
    merchant_uuid uuid;
    restaurant_pk bigint;
    active_listing_uuid uuid := '8f6d9b9c-36d8-44ae-9a35-d263e0dfd2f7';
    active_donation_uuid uuid := '0f4a85e7-6fd0-4d20-8a52-23dfe43a0f10';
    active_request_uuid uuid := '6a12e5aa-5080-40cc-950b-3c8b65b35a9a';
    completed_listing_uuid uuid := '72563d2e-86e2-4ed2-b230-5ca4e3f7d26c';
    completed_donation_uuid uuid := 'ba7f1c4a-2ff5-4ee6-9d86-2e119f7dcda4';
    completed_request_uuid uuid := 'cffce283-6b7a-4d25-b2cb-4ea34161acaf';
    impact_report_uuid uuid := 'b15ee0bb-2284-49af-ad50-fd7760f1f14a';
BEGIN
    SELECT id
    INTO charity_uuid
    FROM users_user
    WHERE email = 'charity1@tawfir.dz'
      AND user_type = 'charity'
    LIMIT 1;

    IF charity_uuid IS NULL THEN
        RAISE EXCEPTION 'No charity user found for charity1@tawfir.dz.';
    END IF;

    SELECT id
    INTO merchant_uuid
    FROM users_user
    WHERE email = 'zinedinerabouh@gmail.com'
      AND user_type = 'merchant'
    LIMIT 1;

    IF merchant_uuid IS NULL THEN
        SELECT id
        INTO merchant_uuid
        FROM users_user
        WHERE user_type = 'merchant'
        ORDER BY email
        LIMIT 1;
    END IF;

    IF merchant_uuid IS NULL THEN
        RAISE EXCEPTION 'No merchant user found for donation status seed.';
    END IF;

    SELECT id
    INTO restaurant_pk
    FROM listings_category
    WHERE slug = 'restaurant'
    LIMIT 1;

    IF restaurant_pk IS NULL THEN
        SELECT id
        INTO restaurant_pk
        FROM listings_category
        ORDER BY id
        LIMIT 1;
    END IF;

    IF restaurant_pk IS NULL THEN
        RAISE EXCEPTION 'No listing category found for donation status seed.';
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
        active_listing_uuid,
        merchant_uuid,
        restaurant_pk,
        'Active Charity Meal Trays',
        '',
        'Plateaux Repas Actifs',
        'Fresh meal trays reserved for charity pickup today.',
        '',
        'Plateaux repas frais reserves pour une collecte associative aujourd hui.',
        0.00,
        0.00,
        'DZD',
        12,
        12,
        'tray',
        'A',
        'active',
        now() + interval '30 minutes',
        now() + interval '6 hours',
        true,
        '["gluten"]'::jsonb,
        '{"is_halal": true}'::jsonb,
        NULL,
        0,
        0.0
    )
    ON CONFLICT (id) DO UPDATE SET
        updated_at = now(),
        status = 'active',
        pickup_start = now() + interval '30 minutes',
        pickup_end = now() + interval '6 hours',
        quantity_available = 12,
        is_donation = true;

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
        now() - interval '1 day',
        now(),
        completed_listing_uuid,
        merchant_uuid,
        restaurant_pk,
        'Completed Charity Couscous Donation',
        '',
        'Don Couscous Termine',
        'Couscous portions already collected and distributed by the charity.',
        '',
        'Portions de couscous deja collectees et distribuees par l association.',
        0.00,
        0.00,
        'DZD',
        18,
        0,
        'portion',
        'A',
        'donated',
        now() - interval '8 hours',
        now() - interval '2 hours',
        true,
        '["gluten"]'::jsonb,
        '{"is_halal": true}'::jsonb,
        NULL,
        0,
        0.0
    )
    ON CONFLICT (id) DO UPDATE SET
        updated_at = now(),
        status = 'donated',
        pickup_start = now() - interval '8 hours',
        pickup_end = now() - interval '2 hours',
        quantity_available = 0,
        is_donation = true;

    INSERT INTO listings_listingphoto (photo_url, is_primary, "order", listing_id)
    SELECT
        'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&q=80',
        true,
        1,
        active_listing_uuid
    WHERE NOT EXISTS (
        SELECT 1
        FROM listings_listingphoto
        WHERE listing_id = active_listing_uuid
          AND is_primary = true
    );

    INSERT INTO listings_listingphoto (photo_url, is_primary, "order", listing_id)
    SELECT
        'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800&q=80',
        true,
        1,
        completed_listing_uuid
    WHERE NOT EXISTS (
        SELECT 1
        FROM listings_listingphoto
        WHERE listing_id = completed_listing_uuid
          AND is_primary = true
    );

    INSERT INTO donations_donation (
        created_at,
        updated_at,
        id,
        listing_id,
        merchant_id,
        assigned_charity_id,
        status,
        collection_start,
        collection_end,
        qr_hash,
        qr_expires_at,
        notes,
        collected_at
    )
    VALUES (
        now(),
        now(),
        active_donation_uuid,
        active_listing_uuid,
        merchant_uuid,
        charity_uuid,
        'assigned',
        now() + interval '30 minutes',
        now() + interval '6 hours',
        'seed-charity1-active-qr',
        now() + interval '6 hours',
        'Seed active donation assigned to charity1@tawfir.dz.',
        NULL
    )
    ON CONFLICT (id) DO UPDATE SET
        updated_at = now(),
        assigned_charity_id = charity_uuid,
        status = 'assigned',
        collection_start = now() + interval '30 minutes',
        collection_end = now() + interval '6 hours',
        qr_hash = 'seed-charity1-active-qr',
        qr_expires_at = now() + interval '6 hours',
        collected_at = NULL;

    INSERT INTO donations_donation (
        created_at,
        updated_at,
        id,
        listing_id,
        merchant_id,
        assigned_charity_id,
        status,
        collection_start,
        collection_end,
        qr_hash,
        qr_expires_at,
        notes,
        collected_at
    )
    VALUES (
        now() - interval '1 day',
        now(),
        completed_donation_uuid,
        completed_listing_uuid,
        merchant_uuid,
        charity_uuid,
        'collected',
        now() - interval '8 hours',
        now() - interval '2 hours',
        'seed-charity1-completed-qr',
        now() - interval '1 hour',
        'Seed completed donation collected by charity1@tawfir.dz.',
        now() - interval '90 minutes'
    )
    ON CONFLICT (id) DO UPDATE SET
        updated_at = now(),
        assigned_charity_id = charity_uuid,
        status = 'collected',
        collection_start = now() - interval '8 hours',
        collection_end = now() - interval '2 hours',
        qr_hash = 'seed-charity1-completed-qr',
        qr_expires_at = now() - interval '1 hour',
        collected_at = now() - interval '90 minutes';

    INSERT INTO donations_donationrequest (
        created_at,
        updated_at,
        id,
        donation_id,
        charity_id,
        status,
        message,
        responded_at
    )
    VALUES (
        now(),
        now(),
        active_request_uuid,
        active_donation_uuid,
        charity_uuid,
        'approved',
        'Seed active pickup for charity1@tawfir.dz.',
        now()
    )
    ON CONFLICT ON CONSTRAINT unique_donation_charity_request DO UPDATE SET
        updated_at = now(),
        status = 'approved',
        message = EXCLUDED.message,
        responded_at = now();

    INSERT INTO donations_donationrequest (
        created_at,
        updated_at,
        id,
        donation_id,
        charity_id,
        status,
        message,
        responded_at
    )
    VALUES (
        now() - interval '1 day',
        now(),
        completed_request_uuid,
        completed_donation_uuid,
        charity_uuid,
        'collected',
        'Seed completed pickup for charity1@tawfir.dz.',
        now() - interval '90 minutes'
    )
    ON CONFLICT ON CONSTRAINT unique_donation_charity_request DO UPDATE SET
        updated_at = now(),
        status = 'collected',
        message = EXCLUDED.message,
        responded_at = now() - interval '90 minutes';

    INSERT INTO donations_impactreport (
        created_at,
        updated_at,
        id,
        donation_id,
        charity_id,
        families_helped,
        meals_provided,
        weight_kg,
        notes,
        photo_proof_urls
    )
    VALUES (
        now() - interval '1 hour',
        now(),
        impact_report_uuid,
        completed_donation_uuid,
        charity_uuid,
        8,
        36,
        18.00,
        'Seed impact report for completed charity1 donation.',
        '[]'::jsonb
    )
    ON CONFLICT (donation_id) DO UPDATE SET
        updated_at = now(),
        charity_id = charity_uuid,
        families_helped = 8,
        meals_provided = 36,
        weight_kg = 18.00,
        notes = EXCLUDED.notes;

    RAISE NOTICE 'Ensured active donation % and completed donation % for charity1@tawfir.dz.',
        active_donation_uuid,
        completed_donation_uuid;
END $$;
