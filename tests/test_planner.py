from omada_batch.services.planner import generate_plan


def test_generate_plan_count_and_vlan_range():
    plans, warnings = generate_plan(
        name_prefix="LAN",
        start_ip="10.0.0.0",
        prefix_len=24,
        count=3,
        start_vlan=100,
        dhcp_start_offset=10,
        dhcp_end_offset=10,
    )
    assert len(plans) == 3
    assert plans[0].vlan_id == 100
    assert plans[2].vlan_id == 102
    assert isinstance(warnings, list)
