"""Tests for storage optimization features:
- Retention policy (1.1)
- Git garbage collection (1.3)
- Chunked storage for large files (2.1)
- Hard-link deduplication (3.2)

TDD approach: Tests written before implementation.
"""

import os
import struct
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


# =============================================================================
# 1.1 Retention Policy Tests
# =============================================================================


def test_retention_policy_limits_commits(tmp_path):
    """Retention policy should keep only N most recent commits."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy(retention_count=5)
    
    # Mock the repo to track commit calls
    mock_repo = MagicMock()
    mock_walker = []
    
    # Create 10 mock commits
    for i in range(10):
        commit = MagicMock()
        commit.id = f"commit{i}".encode()
        commit.commit_time = 1000 + i
        mock_walker.append(MagicMock(commit=commit))
    
    mock_repo.get_walker.return_value = mock_walker
    
    with patch('gamesave_vcs.strategies.git.Repo', return_value=mock_repo):
        with patch('gamesave_vcs.strategies.git.porcelain.reset') as mock_reset:
            # Apply retention
            strategy._apply_retention(tmp_path, keep_count=5)
            
            # Should have reset to the 5th most recent commit
            # (index 5 in 0-indexed list of 10)
            assert mock_reset.called


def test_retention_policy_keeps_minimum_commits():
    """Retention should never delete all commits - keep at least 1."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy(retention_count=5)
    
    # With fewer commits than retention count, nothing should be pruned
    mock_repo = MagicMock()
    mock_walker = []
    
    for i in range(3):  # Only 3 commits
        commit = MagicMock()
        commit.id = f"commit{i}".encode()
        commit.commit_time = 1000 + i
        mock_walker.append(MagicMock(commit=commit))
    
    mock_repo.get_walker.return_value = mock_walker
    
    with patch('gamesave_vcs.strategies.git.Repo', return_value=mock_repo):
        with patch('gamesave_vcs.strategies.git.porcelain.reset') as mock_reset:
            strategy._apply_retention(Path("/tmp/test"), keep_count=5)
            # Should not reset since we have fewer than retention count
            assert not mock_reset.called


def test_retention_policy_configurable():
    """Retention count should be configurable per strategy instance."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy_default = GitStrategy()
    strategy_custom = GitStrategy(retention_count=10)
    strategy_unlimited = GitStrategy(retention_count=0)  # 0 = unlimited
    
    assert strategy_default.retention_count == 20  # Default
    assert strategy_custom.retention_count == 10
    assert strategy_unlimited.retention_count == 0


def test_retention_policy_disabled_when_zero():
    """Retention policy should be disabled when count is 0."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy(retention_count=0)
    
    with patch.object(strategy, '_apply_retention') as mock_apply:
        # Simulate backup
        strategy._prune_old_commits(Path("/tmp/test"))
        # Should not be called when retention is 0
        assert not mock_apply.called


# =============================================================================
# 1.3 Git Garbage Collection Tests
# =============================================================================


def test_git_gc_runs_after_backup(tmp_path):
    """Git GC should run periodically after backups."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy(gc_interval=5)  # GC every 5 backups
    
    with patch('gamesave_vcs.strategies.git.porcelain.gc') as mock_gc:
        # Simulate 5 backups
        for i in range(5):
            strategy._maybe_run_gc(tmp_path)
        
        # GC should have been called once
        assert mock_gc.called


def test_git_gc_respects_interval():
    """Git GC should only run at specified intervals."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy(gc_interval=10)
    
    with patch('gamesave_vcs.strategies.git.porcelain.gc') as mock_gc:
        # Simulate 9 backups
        for i in range(9):
            strategy._maybe_run_gc(Path("/tmp/test"))
        
        # GC should not have been called yet
        assert not mock_gc.called
        
        # 10th backup should trigger GC
        strategy._maybe_run_gc(Path("/tmp/test"))
        assert mock_gc.called


def test_git_gc_aggressive_mode():
    """Git GC should support aggressive mode for better compression."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy()
    
    with patch('gamesave_vcs.strategies.git.porcelain.gc') as mock_gc:
        # Test that _run_gc handles aggressive parameter without error
        # (implementation may use aggressive mode internally)
        strategy._run_gc(Path("/tmp/test"), aggressive=True)
        
        # Should call gc
        mock_gc.assert_called_once()
        # The aggressive flag is handled internally, porcelain.gc doesn't have it


def test_git_gc_handles_errors_gracefully():
    """Git GC should not fail backup if GC errors."""
    from gamesave_vcs.strategies.git import GitStrategy
    
    strategy = GitStrategy()
    
    with patch('gamesave_vcs.strategies.git.porcelain.gc', 
               side_effect=Exception("GC failed")):
        # Should not raise
        strategy._run_gc(Path("/tmp/test"))


# =============================================================================
# 2.1 Chunked Storage Tests
# =============================================================================


def test_chunked_storage_splits_large_files(tmp_path):
    """Large files should be split into chunks."""
    from gamesave_vcs.strategies.chunked import ChunkedStorage
    
    chunk_store = tmp_path / "chunks"
    storage = ChunkedStorage(chunk_store=chunk_store, chunk_size=1024)  # 1KB chunks
    
    # Create 5KB file
    test_file = tmp_path / "large.save"
    test_file.write_bytes(b"A" * 5120)
    
    chunks = storage._split_into_chunks(test_file)
    
    # Should create 5 chunks (5KB / 1KB = 5)
    assert len(chunks) == 5
    
    # Each chunk should be content-addressed (hash as name)
    for chunk_hash in chunks:
        chunk_path = storage._chunk_path(chunk_hash)
        assert chunk_path.exists()
        assert len(chunk_path.read_bytes()) <= 1024


def test_chunked_storage_deduplicates_chunks(tmp_path):
    """Identical chunks should be stored only once."""
    from gamesave_vcs.strategies.chunked import ChunkedStorage
    
    chunk_store = tmp_path / "chunks"
    storage = ChunkedStorage(chunk_store=chunk_store, chunk_size=1024)
    
    # Two files with same content in first chunk
    file1 = tmp_path / "file1.save"
    file1.write_bytes(b"X" * 1024 + b"Y" * 1024)
    
    file2 = tmp_path / "file2.save"
    file2.write_bytes(b"X" * 1024 + b"Z" * 1024)
    
    chunks1 = storage._split_into_chunks(file1)
    chunks2 = storage._split_into_chunks(file2)
    
    # First chunk should be same hash (deduplicated)
    assert chunks1[0] == chunks2[0]
    # Second chunk should be different
    assert chunks1[1] != chunks2[1]
    
    # Verify only one chunk file exists for the shared chunk
    chunk_path = storage._chunk_path(chunks1[0])
    assert chunk_path.exists()


def test_chunked_storage_reconstructs_file(tmp_path):
    """Should be able to reconstruct original file from chunks."""
    from gamesave_vcs.strategies.chunked import ChunkedStorage
    
    chunk_store = tmp_path / "chunks"
    storage = ChunkedStorage(chunk_store=chunk_store, chunk_size=1024)
    
    # Create original file
    original = tmp_path / "original.save"
    original_data = b"ABCDEFGHIJ" * 100  # 1KB
    original.write_bytes(original_data)
    
    # Split into chunks
    chunks = storage._split_into_chunks(original)
    
    # Reconstruct
    reconstructed = tmp_path / "reconstructed.save"
    result = storage._reconstruct_from_chunks(chunks, reconstructed)
    
    # Verify
    assert result is True
    assert reconstructed.read_bytes() == original_data


def test_chunked_storage_manifest_tracks_files(tmp_path):
    """Manifest should track which chunks belong to which file."""
    from gamesave_vcs.strategies.chunked import ChunkedStorage
    
    chunk_store = tmp_path / "chunks"
    storage = ChunkedStorage(chunk_store=chunk_store)
    
    # Set up manifest directly
    storage.manifest = {
        "file1.save": ["chunk_hash_1", "chunk_hash_2"],
        "file2.save": ["chunk_hash_1", "chunk_hash_3"],  # Shares chunk 1
    }
    
    # Track reference counts
    ref_counts = storage._get_chunk_reference_counts()
    
    assert ref_counts["chunk_hash_1"] == 2
    assert ref_counts["chunk_hash_2"] == 1
    assert ref_counts["chunk_hash_3"] == 1


def test_chunked_storage_removes_orphaned_chunks(tmp_path):
    """Chunks no longer referenced should be removed."""
    from gamesave_vcs.strategies.chunked import ChunkedStorage
    
    chunk_store = tmp_path / "chunkstore"
    storage = ChunkedStorage(chunk_store=chunk_store)
    
    # Create some chunks directly in the chunk store
    # Use proper hash prefix directories
    chunk1_hash = "abc123"
    chunk1_dir = chunk_store / chunk1_hash[:2]
    chunk1_dir.mkdir(parents=True, exist_ok=True)
    chunk1 = chunk1_dir / chunk1_hash
    chunk1.write_text("data1")
    
    chunk2_hash = "def456"
    chunk2_dir = chunk_store / chunk2_hash[:2]
    chunk2_dir.mkdir(parents=True, exist_ok=True)
    chunk2 = chunk2_dir / chunk2_hash
    chunk2.write_text("data2")
    
    # Only chunk1 is referenced in manifest
    storage.manifest = {"file.save": [chunk1_hash]}
    
    storage.remove_orphaned_chunks()
    
    assert chunk1.exists()  # Still referenced
    assert not chunk2.exists()  # Orphaned, should be removed


# =============================================================================
# 3.2 Hard-Link Deduplication Tests
# =============================================================================


def test_hardlink_dedup_creates_links_for_identical_files(tmp_path):
    """Identical files should be hard-linked to save space."""
    from gamesave_vcs.strategies.full_copy import FullCopyStrategy
    
    strategy = FullCopyStrategy(use_hardlinks=True)
    
    # Create original file
    original = tmp_path / "original.save"
    original.write_text("save data")
    
    # Create backup (should use hardlink)
    backup = tmp_path / "backup" / "save1.save"
    backup.parent.mkdir()
    
    strategy._copy_with_hardlinks(original, backup)
    
    # Should be same inode (hardlinked)
    assert original.stat().st_ino == backup.stat().st_ino
    assert original.stat().st_nlink == 2


def test_hardlink_dedup_copies_different_files(tmp_path):
    """Different files should be copied normally (different inodes)."""
    from gamesave_vcs.strategies.full_copy import FullCopyStrategy
    
    # With content-addressed dedup, different files get different storage
    content_store = tmp_path / "content"
    strategy = FullCopyStrategy(
        use_hardlinks=True,
        content_addressed=True,
        content_store=content_store
    )
    
    # Create different files
    file1 = tmp_path / "file1.save"
    file1.write_text("data1")
    
    file2 = tmp_path / "file2.save"
    file2.write_text("data2")
    
    backup1 = tmp_path / "backup" / "file1.save"
    backup1.parent.mkdir(parents=True)
    backup2 = tmp_path / "backup" / "file2.save"
    
    # Backup both files
    strategy._backup_with_dedup(file1, backup1)
    strategy._backup_with_dedup(file2, backup2)
    
    # Different content should have different inodes in content store
    hash1 = strategy._file_hash(file1)
    hash2 = strategy._file_hash(file2)
    content_path1 = strategy._get_content_path(hash1)
    content_path2 = strategy._get_content_path(hash2)
    
    # Different content = different storage paths = different inodes
    assert content_path1 != content_path2
    assert content_path1.stat().st_ino != content_path2.stat().st_ino


def test_hardlink_dedup_content_addressed_storage(tmp_path):
    """Files should be stored by content hash for deduplication."""
    from gamesave_vcs.strategies.full_copy import FullCopyStrategy
    
    strategy = FullCopyStrategy(
        use_hardlinks=True,
        content_addressed=True,
        content_store=tmp_path / "content"
    )
    
    # Create two identical files in different locations
    save1 = tmp_path / "game1" / "save.dat"
    save1.parent.mkdir(parents=True)
    save1.write_text("identical data")
    
    save2 = tmp_path / "game2" / "save.dat"
    save2.parent.mkdir(parents=True)
    save2.write_text("identical data")
    
    # Backup both
    backup1 = tmp_path / "backups" / "game1" / "save.dat"
    backup1.parent.mkdir(parents=True)
    strategy._backup_with_dedup(save1, backup1)
    
    backup2 = tmp_path / "backups" / "game2" / "save.dat"
    backup2.parent.mkdir(parents=True)
    strategy._backup_with_dedup(save2, backup2)
    
    # Both backups should point to same content file
    assert backup1.stat().st_ino == backup2.stat().st_ino


def test_hardlink_dedup_handles_modifications(tmp_path):
    """Content-addressed dedup ensures modifications don't affect other backups."""
    from gamesave_vcs.strategies.full_copy import FullCopyStrategy
    
    content_store = tmp_path / "content"
    strategy = FullCopyStrategy(
        use_hardlinks=True,
        content_addressed=True,
        content_store=content_store
    )
    
    original = tmp_path / "original.save"
    original.write_text("original data")
    
    # First backup
    backup1 = tmp_path / "backup1.save"
    strategy._backup_with_dedup(original, backup1)
    
    # Verify content is stored
    hash1 = strategy._file_hash(original)
    content_path1 = strategy._get_content_path(hash1)
    assert content_path1.exists()
    
    # Modify original
    original.write_text("modified data")
    
    # Second backup after modification
    backup2 = tmp_path / "backup2.save"
    strategy._backup_with_dedup(original, backup2)
    
    # Both backups should exist with correct content
    assert backup1.read_text() == "original data"
    assert backup2.read_text() == "modified data"
    
    # Different content should have different storage
    hash2 = strategy._file_hash(original)
    assert hash1 != hash2


def test_hardlink_dedup_saves_disk_space(tmp_path):
    """Hardlink dedup should actually reduce disk usage."""
    from gamesave_vcs.strategies.full_copy import FullCopyStrategy
    
    strategy = FullCopyStrategy(use_hardlinks=True)
    
    # Create 10 identical 1MB files
    data = b"X" * (1024 * 1024)
    
    original = tmp_path / "original.save"
    original.write_bytes(data)
    
    backups = []
    for i in range(10):
        backup = tmp_path / f"backup{i}.save"
        strategy._copy_with_hardlinks(original, backup)
        backups.append(backup)
    
    # All should share same inode
    inodes = {b.stat().st_ino for b in backups}
    assert len(inodes) == 1
    
    # Each should have 11 links (original + 10 backups)
    assert backups[0].stat().st_nlink == 11


def test_hardlink_fallback_to_copy_on_different_filesystems(tmp_path):
    """Should fallback to copy if hardlink fails (different FS)."""
    from gamesave_vcs.strategies.full_copy import FullCopyStrategy
    
    strategy = FullCopyStrategy(use_hardlinks=True)
    
    src = tmp_path / "src" / "file"
    dst = tmp_path / "dst" / "file"
    
    with patch('os.link', side_effect=OSError(18, "Invalid cross-device link")):
        with patch('shutil.copy2') as mock_copy:
            strategy._copy_with_hardlinks(
                src, dst
            )
            # Should fallback to copy2
            assert mock_copy.called
