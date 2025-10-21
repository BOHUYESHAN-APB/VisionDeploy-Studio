from app.ui_skeleton_ctk import get_context_info


def test_get_context_info_parses_context():
    ctx = {'project_root': '/proj', 'resources_dir': '/proj/resources', 'mirror': 'cn'}
    info = get_context_info(ctx)
    assert info['project_root'] == '/proj'
    assert info['resources_dir'] == '/proj/resources'
    assert info['mirror'] == 'cn'
