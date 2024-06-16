import pytest
from GeneratorID.GeneratorID import GeneratorID


@pytest.fixture
def uid_generator():
    uid_generator_instance = GeneratorID()
    yield uid_generator_instance


def test_get_cpu_serial(uid_generator):
    cpu_sn = uid_generator._get_cpu_serial()
    assert cpu_sn == "1000000057628238"


def test_get_disk_serial(uid_generator):
    disk_sn = uid_generator._get_disk_serial()
    assert disk_sn == "0x9b04c02b"


def test_get_network_card_serial(uid_generator):
    disk_sn = uid_generator._get_disk_serial()
    assert disk_sn == "0x9b04c02b"


def test_generate_uid(uid_generator):
    uid = uid_generator.generate_uid()
    assert uid == "a4115ca47d9b1f000be1806e315124624e7b10ea2fd4439c6027557e8285095a"
