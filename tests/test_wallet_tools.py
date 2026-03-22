#!/usr/bin/env python3
"""
Unit Tests for RustChain MCP Wallet Tools
==========================================

Tests for the wallet management tools:
- wallet_create
- wallet_balance
- wallet_history
- wallet_list
- wallet_export
- wallet_import
- wallet_transfer_signed

Run with: pytest tests/test_wallet_tools.py -v
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
import pytest

# Import the crypto module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "rustchain_mcp"))

from rustchain_crypto import RustChainCrypto, create_wallet, sign_transaction


class TestRustChainCrypto:
    """Tests for the RustChainCrypto class."""
    
    @pytest.fixture
    def temp_keystore(self):
        """Create a temporary keystore directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def crypto(self, temp_keystore):
        """Create a RustChainCrypto instance with temp keystore."""
        return RustChainCrypto(keystore_dir=Path(temp_keystore))
    
    def test_generate_mnemonic_12_words(self, crypto):
        """Test 12-word mnemonic generation."""
        mnemonic = crypto.generate_mnemonic(strength=128)
        words = mnemonic.split()
        
        assert len(words) == 12, "Should generate 12 words with 128-bit strength"
        assert all(word.isalpha() for word in words), "All words should be alphabetic"
    
    def test_generate_mnemonic_24_words(self, crypto):
        """Test 24-word mnemonic generation."""
        mnemonic = crypto.generate_mnemonic(strength=256)
        words = mnemonic.split()
        
        assert len(words) == 24, "Should generate 24 words with 256-bit strength"
    
    def test_mnemonic_to_seed(self, crypto):
        """Test mnemonic to seed conversion."""
        mnemonic = "abandon ability able about above absent absorb abstract absurd abuse access accident"
        seed = crypto.mnemonic_to_seed(mnemonic)
        
        assert len(seed) == 64, "Seed should be 64 bytes"
        assert isinstance(seed, bytes), "Seed should be bytes"
    
    def test_mnemonic_to_seed_with_passphrase(self, crypto):
        """Test mnemonic to seed with passphrase."""
        mnemonic = "abandon ability able about above absent absorb abstract absurd abuse access accident"
        
        seed1 = crypto.mnemonic_to_seed(mnemonic)
        seed2 = crypto.mnemonic_to_seed(mnemonic, passphrase="test123")
        
        assert seed1 != seed2, "Passphrase should change the seed"
    
    def test_generate_keypair(self, crypto):
        """Test Ed25519 keypair generation."""
        private_key, public_key = crypto.generate_keypair()
        
        assert len(private_key) == 32, "Private key should be 32 bytes"
        assert len(public_key) == 32, "Public key should be 32 bytes"
    
    def test_generate_keypair_from_seed(self, crypto):
        """Test deterministic keypair from seed."""
        seed = b'\x01' * 32
        
        priv1, pub1 = crypto.generate_keypair(seed)
        priv2, pub2 = crypto.generate_keypair(seed)
        
        assert priv1 == priv2, "Same seed should produce same private key"
        assert pub1 == pub2, "Same seed should produce same public key"
    
    def test_derive_address(self, crypto):
        """Test address derivation from public key."""
        _, public_key = crypto.generate_keypair()
        address = crypto.derive_address(public_key)
        
        assert address.startswith("RTC"), "Address should start with RTC"
        assert len(address) == 43, "Address should be 43 chars (RTC + 40 hex)"
    
    def test_sign_and_verify(self, crypto):
        """Test message signing and verification."""
        private_key, public_key = crypto.generate_keypair()
        message = b"Test message for signing"
        
        signature = crypto.sign_message(private_key, message)
        assert len(signature) == 64, "Ed25519 signature should be 64 bytes"
        
        # Verify signature
        is_valid = crypto.verify_signature(public_key, message, signature)
        assert is_valid, "Signature should be valid"
    
    def test_verify_invalid_signature(self, crypto):
        """Test verification of invalid signature."""
        private_key, public_key = crypto.generate_keypair()
        message = b"Original message"
        
        signature = crypto.sign_message(private_key, message)
        
        # Try to verify with different message
        is_valid = crypto.verify_signature(public_key, b"Different message", signature)
        assert not is_valid, "Signature should be invalid for different message"
    
    def test_encrypt_decrypt_keystore(self, crypto):
        """Test keystore encryption and decryption."""
        private_key, public_key = crypto.generate_keypair()
        address = crypto.derive_address(public_key)
        mnemonic = "test mnemonic phrase"
        
        # Encrypt
        keystore = crypto.encrypt_keystore(private_key, "test-password", address, mnemonic)
        
        assert "crypto" in keystore
        assert keystore["address"] == address
        assert keystore["version"] == 1
        
        # Decrypt
        decrypted = crypto.decrypt_keystore(keystore, "test-password")
        
        assert decrypted["private_key"] == private_key
        assert decrypted["address"] == address
        assert decrypted["mnemonic"] == mnemonic
    
    def test_decrypt_with_wrong_password(self, crypto):
        """Test decryption with wrong password fails."""
        private_key, public_key = crypto.generate_keypair()
        address = crypto.derive_address(public_key)
        
        keystore = crypto.encrypt_keystore(private_key, "correct-password", address)
        
        with pytest.raises(ValueError):
            crypto.decrypt_keystore(keystore, "wrong-password")
    
    def test_save_and_load_keystore(self, crypto):
        """Test saving and loading keystore."""
        private_key, public_key = crypto.generate_keypair()
        address = crypto.derive_address(public_key)
        
        keystore = crypto.encrypt_keystore(private_key, "test-password", address)
        filepath = crypto.save_keystore(keystore)
        
        assert filepath.exists()
        
        # Load
        loaded = crypto.load_keystore(address)
        assert loaded == keystore
    
    def test_list_keystores(self, crypto):
        """Test listing keystores."""
        # Create multiple wallets
        for i in range(3):
            private_key, public_key = crypto.generate_keypair()
            address = crypto.derive_address(public_key)
            keystore = crypto.encrypt_keystore(private_key, f"password{i}", address)
            crypto.save_keystore(keystore)
        
        keystores = crypto.list_keystores()
        
        assert len(keystores) == 3
        assert all("address" in k for k in keystores)
    
    def test_delete_keystore(self, crypto):
        """Test deleting keystore."""
        private_key, public_key = crypto.generate_keypair()
        address = crypto.derive_address(public_key)
        
        keystore = crypto.encrypt_keystore(private_key, "test-password", address)
        crypto.save_keystore(keystore)
        
        # Verify exists
        assert crypto.load_keystore(address) is not None
        
        # Delete
        result = crypto.delete_keystore(address)
        assert result is True
        
        # Verify deleted
        assert crypto.load_keystore(address) is None


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.fixture
    def temp_keystore(self):
        """Create a temporary keystore directory."""
        temp_dir = tempfile.mkdtemp()
        
        # Create a unique keystore path
        keystore_path = Path(temp_dir) / ".rustchain" / "mcp_wallets"
        keystore_path.mkdir(parents=True, exist_ok=True)
        
        yield keystore_path
        
        shutil.rmtree(temp_dir)
    
    def test_create_wallet(self, temp_keystore):
        """Test wallet creation convenience function."""
        crypto = RustChainCrypto(keystore_dir=temp_keystore)
        result = create_wallet(name="test-wallet", password="test-password")
        
        assert "address" in result
        assert result["name"] == "test-wallet"
        assert result["created"] is True
        assert "RTC" in result["address"]
        assert "password" not in result  # Password was provided, not generated
    
    def test_create_wallet_random_password(self, temp_keystore):
        """Test wallet creation with random password."""
        crypto = RustChainCrypto(keystore_dir=temp_keystore)
        result = create_wallet(name="test-wallet")
        
        assert "password" in result  # Random password should be returned
        assert len(result["password"]) > 0
    
    def test_sign_transaction(self, temp_keystore):
        """Test transaction signing."""
        crypto = RustChainCrypto(keystore_dir=temp_keystore)
        # Create a wallet
        private_key, _ = crypto.generate_keypair()
        
        result = sign_transaction(
            private_key=private_key,
            from_address="RTC1a2b3c4d",
            to_address="RTC5e6f7g8h",
            amount=10.0,
            nonce=1234567890,
            memo="Test transaction"
        )
        
        assert "signature" in result
        assert "public_key" in result
        assert "nonce" in result
        assert len(result["signature"]) == 128  # 64 bytes in hex


class TestWalletTools:
    """Tests for MCP wallet tools (integration tests)."""
    
    @pytest.fixture
    def isolated_keystore(self):
        """Create an isolated keystore directory for each test."""
        temp_dir = tempfile.mkdtemp()
        keystore_path = Path(temp_dir) / ".rustchain" / "mcp_wallets"
        keystore_path.mkdir(parents=True, exist_ok=True)
        
        # Set environment variable to use isolated keystore
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = temp_dir
        
        yield keystore_path
        
        # Restore
        if original_home:
            os.environ["HOME"] = original_home
        else:
            del os.environ["HOME"]
        
        shutil.rmtree(temp_dir)
    
    def test_wallet_create_and_list(self, isolated_keystore):
        """Test creating and listing wallets."""
        from rustchain_mcp.server import wallet_create, wallet_list
        
        # Create wallet
        result = wallet_create(name="test-wallet", password="test-password")
        assert result["created"] is True
        
        # List wallets
        wallets = wallet_list()
        assert wallets["total"] >= 1
        # Find our wallet
        our_wallet = next((w for w in wallets["wallets"] if w["address"] == result["address"]), None)
        assert our_wallet is not None
    
    def test_wallet_export_import(self, isolated_keystore):
        """Test exporting and importing wallet."""
        from rustchain_mcp.server import wallet_create, wallet_export, wallet_import, wallet_list
        from rustchain_mcp.rustchain_crypto import RustChainCrypto
        
        # Create wallet
        created = wallet_create(name="test-wallet", password="test-password")
        address = created["address"]
        
        # Export wallet
        exported = wallet_export(address, "test-password")
        assert "keystore" in exported
        
        # Delete wallet
        crypto = RustChainCrypto()
        crypto.delete_keystore(address)
        
        # Verify deleted
        wallets = wallet_list()
        our_wallet = next((w for w in wallets["wallets"] if w["address"] == address), None)
        assert our_wallet is None
        
        # Import wallet
        imported = wallet_import(
            keystore=exported["keystore"],
            password="test-password",
            name="restored-wallet"
        )
        assert imported["imported"] is True
        assert imported["address"] == address
    
    def test_wallet_import_mnemonic(self, isolated_keystore):
        """Test importing wallet from mnemonic."""
        from rustchain_mcp.server import wallet_import
        from rustchain_mcp.rustchain_crypto import RustChainCrypto
        
        # Generate a unique mnemonic for this test
        crypto = RustChainCrypto(keystore_dir=isolated_keystore)
        mnemonic = crypto.generate_mnemonic()
        
        result = wallet_import(
            mnemonic=mnemonic,
            password="test-password",
            name="imported-wallet"
        )
        
        assert result["imported"] is True
        assert result["method"] == "mnemonic"
        assert "RTC" in result["address"]
    
    def test_wallet_import_invalid_mnemonic(self, isolated_keystore):
        """Test importing with invalid mnemonic."""
        from rustchain_mcp.server import wallet_import
        
        # Wrong number of words
        result = wallet_import(
            mnemonic="abandon ability able",
            password="test-password"
        )
        
        assert "error" in result


class TestSecurityFeatures:
    """Tests for security features."""
    
    @pytest.fixture
    def temp_keystore(self):
        """Create a temporary keystore directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def crypto(self, temp_keystore):
        """Create a RustChainCrypto instance."""
        return RustChainCrypto(keystore_dir=Path(temp_keystore))
    
    def test_private_key_not_in_response(self, crypto):
        """Test that private key is never exposed in responses."""
        result = create_wallet(name="test")
        
        assert "private_key" not in result
        assert "mnemonic" not in result
    
    def test_keystore_permissions(self, crypto):
        """Test that keystore files have restrictive permissions."""
        private_key, public_key = crypto.generate_keypair()
        address = crypto.derive_address(public_key)
        
        keystore = crypto.encrypt_keystore(private_key, "test-password", address)
        filepath = crypto.save_keystore(keystore)
        
        # Check file permissions (should be 0o600 on Unix)
        # On Windows, this may not apply
        if os.name != 'nt':
            mode = filepath.stat().st_mode & 0o777
            assert mode == 0o600, f"Expected permissions 0o600, got {oct(mode)}"
    
    def test_deterministic_addresses(self, crypto):
        """Test that same mnemonic always produces same address."""
        mnemonic = crypto.generate_mnemonic()
        
        # Generate keypair twice from same mnemonic
        seed1 = crypto.mnemonic_to_seed(mnemonic)
        priv1, pub1 = crypto.generate_keypair(seed1)
        addr1 = crypto.derive_address(pub1)
        
        seed2 = crypto.mnemonic_to_seed(mnemonic)
        priv2, pub2 = crypto.generate_keypair(seed2)
        addr2 = crypto.derive_address(pub2)
        
        assert addr1 == addr2, "Same mnemonic should produce same address"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])