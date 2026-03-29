"""Chunked storage strategy for large file deduplication.

Layer 2.1: Content-defined chunking for efficient storage of large files.
Splits files into chunks, deduplicates at chunk level, enables incremental backups.

Inspired by: Borg Backup, Restic, and other modern backup tools.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from gamesave_vcs.strategies.base import BackupStrategy

logger = logging.getLogger(__name__)


class ChunkedStorage:
    """Content-addressed chunked storage for large files.
    
    Splits files into fixed-size chunks, stores each chunk by its hash,
    and maintains a manifest mapping files to their chunks.
    
    This enables:
    - Deduplication at chunk level
    - Incremental backups (only changed chunks)
    - Efficient storage of large files
    """
    
    DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks
    
    def __init__(
        self,
        chunk_store: Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> None:
        """Initialize chunked storage.
        
        Args:
            chunk_store: Directory to store chunks
            chunk_size: Size of each chunk in bytes
        """
        self.chunk_store = chunk_store
        self.chunk_size = chunk_size
        self.chunk_store.mkdir(parents=True, exist_ok=True)
        
        # Manifest tracks which chunks belong to which files
        self.manifest_path = chunk_store / "manifest.json"
        self.manifest: Dict[str, List[str]] = self._load_manifest()
        
        logger.debug(
            f"ChunkedStorage initialized: store={chunk_store}, "
            f"chunk_size={chunk_size}"
        )

    def _load_manifest(self) -> Dict[str, List[str]]:
        """Load chunk manifest from disk."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load manifest: {e}")
        return {}

    def _save_manifest(self) -> None:
        """Save chunk manifest to disk."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(self.manifest, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save manifest: {e}")

    def _chunk_hash(self, data: bytes) -> str:
        """Compute hash for chunk data."""
        return hashlib.sha256(data).hexdigest()

    def _chunk_path(self, chunk_hash: str) -> Path:
        """Get storage path for a chunk.
        
        Uses hash prefix subdirectories to avoid too many files in one dir.
        """
        # First 2 chars as prefix directory
        prefix = chunk_hash[:2]
        return self.chunk_store / prefix / chunk_hash

    def _store_chunk(self, data: bytes) -> str:
        """Store a chunk and return its hash.
        
        If chunk already exists, just returns the hash (deduplication).
        """
        chunk_hash = self._chunk_hash(data)
        chunk_path = self._chunk_path(chunk_hash)
        
        if chunk_path.exists():
            logger.debug(f"Chunk {chunk_hash[:16]}... already exists")
            return chunk_hash
        
        # Store new chunk
        chunk_path.parent.mkdir(parents=True, exist_ok=True)
        chunk_path.write_bytes(data)
        
        logger.debug(f"Stored chunk {chunk_hash[:16]}... ({len(data)} bytes)")
        return chunk_hash

    def _get_chunk(self, chunk_hash: str) -> Optional[bytes]:
        """Retrieve chunk data by hash."""
        chunk_path = self._chunk_path(chunk_hash)
        if chunk_path.exists():
            return chunk_path.read_bytes()
        return None

    def _split_into_chunks(self, file_path: Path) -> List[str]:
        """Split file into chunks and store them.
        
        Args:
            file_path: Path to file to chunk
            
        Returns:
            List of chunk hashes in order
        """
        chunk_hashes = []
        
        with open(file_path, 'rb') as f:
            while True:
                chunk_data = f.read(self.chunk_size)
                if not chunk_data:
                    break
                
                chunk_hash = self._store_chunk(chunk_data)
                chunk_hashes.append(chunk_hash)
        
        logger.debug(
            f"Split {file_path} into {len(chunk_hashes)} chunks"
        )
        return chunk_hashes

    def _reconstruct_from_chunks(
        self,
        chunk_hashes: List[str],
        output_path: Path
    ) -> bool:
        """Reconstruct file from chunks.
        
        Args:
            chunk_hashes: List of chunk hashes in order
            output_path: Path to write reconstructed file
            
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk_hash in chunk_hashes:
                    chunk_data = self._get_chunk(chunk_hash)
                    if chunk_data is None:
                        logger.error(f"Missing chunk: {chunk_hash}")
                        return False
                    f.write(chunk_data)
            
            logger.debug(f"Reconstructed {output_path} from {len(chunk_hashes)} chunks")
            return True
            
        except IOError as e:
            logger.error(f"Failed to reconstruct file: {e}")
            return False

    def store_file(self, file_path: Path, file_id: str) -> List[str]:
        """Store a file using chunked storage.
        
        Args:
            file_path: Path to file to store
            file_id: Unique identifier for this file
            
        Returns:
            List of chunk hashes
        """
        chunk_hashes = self._split_into_chunks(file_path)
        self.manifest[file_id] = chunk_hashes
        self._save_manifest()
        
        logger.info(
            f"Stored {file_path} as {file_id}: {len(chunk_hashes)} chunks"
        )
        return chunk_hashes

    def retrieve_file(self, file_id: str, output_path: Path) -> bool:
        """Retrieve a file by its ID.
        
        Args:
            file_id: File identifier from store_file
            output_path: Path to write retrieved file
            
        Returns:
            True if successful
        """
        if file_id not in self.manifest:
            logger.error(f"File not found in manifest: {file_id}")
            return False
        
        chunk_hashes = self.manifest[file_id]
        return self._reconstruct_from_chunks(chunk_hashes, output_path)

    def _get_chunk_reference_counts(self) -> Dict[str, int]:
        """Count how many files reference each chunk."""
        ref_counts: Dict[str, int] = {}
        
        for chunk_hashes in self.manifest.values():
            for chunk_hash in chunk_hashes:
                ref_counts[chunk_hash] = ref_counts.get(chunk_hash, 0) + 1
        
        return ref_counts

    def remove_orphaned_chunks(self) -> int:
        """Remove chunks that are no longer referenced.
        
        Returns:
            Number of chunks removed
        """
        ref_counts = self._get_chunk_reference_counts()
        
        # Find all chunks on disk
        chunks_removed = 0
        for prefix_dir in self.chunk_store.iterdir():
            if not prefix_dir.is_dir() or prefix_dir.name == "manifest.json":
                continue
            
            for chunk_file in prefix_dir.iterdir():
                if chunk_file.is_file():
                    chunk_hash = chunk_file.name
                    if ref_counts.get(chunk_hash, 0) == 0:
                        # Orphaned chunk
                        try:
                            chunk_file.unlink()
                            chunks_removed += 1
                            logger.debug(f"Removed orphaned chunk: {chunk_hash}")
                        except IOError as e:
                            logger.warning(f"Failed to remove chunk: {e}")
        
        logger.info(f"Removed {chunks_removed} orphaned chunks")
        return chunks_removed

    def delete_file(self, file_id: str) -> bool:
        """Delete a file from the manifest (chunks are removed by cleanup).
        
        Args:
            file_id: File identifier to delete
            
        Returns:
            True if file was found and removed
        """
        if file_id not in self.manifest:
            return False
        
        del self.manifest[file_id]
        self._save_manifest()
        
        logger.info(f"Deleted file from manifest: {file_id}")
        return True

    def get_storage_stats(self) -> Dict:
        """Get statistics about chunk storage.
        
        Returns:
            Dict with stats: total_chunks, total_bytes, dedup_ratio
        """
        total_chunks = 0
        total_bytes = 0
        unique_chunks: Set[str] = set()
        
        for prefix_dir in self.chunk_store.iterdir():
            if not prefix_dir.is_dir():
                continue
            
            for chunk_file in prefix_dir.iterdir():
                if chunk_file.is_file():
                    total_chunks += 1
                    total_bytes += chunk_file.stat().st_size
                    unique_chunks.add(chunk_file.name)
        
        # Calculate logical size (what files would use without dedup)
        logical_chunks = sum(len(hashes) for hashes in self.manifest.values())
        
        dedup_ratio = 0.0
        if logical_chunks > 0:
            dedup_ratio = (1 - len(unique_chunks) / logical_chunks) * 100
        
        return {
            "total_chunks": total_chunks,
            "unique_chunks": len(unique_chunks),
            "total_bytes": total_bytes,
            "logical_chunks": logical_chunks,
            "dedup_ratio_percent": round(dedup_ratio, 2)
        }
