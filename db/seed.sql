INSERT INTO wechat_accounts (
    id,
    name,
    fakeid,
    token,
    cookie,
    page_size,
    days_limit,
    enabled,
    created_at,
    updated_at
)
VALUES (
    'qixiaofu',
    '七小服公众号',
    'MzI3MjYxNDU0MA==',
    '1208987345',
    'yyb_muid=example; wxuin=example; slave_sid=example;',
    5,
    7,
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO NOTHING;
