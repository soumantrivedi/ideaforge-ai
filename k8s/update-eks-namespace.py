#!/usr/bin/env python3
"""
Update namespace and image tags in EKS manifests.
Usage: python3 update-eks-namespace.py <eks_dir> <namespace> <image_tag>
"""
import sys
import os
import re
from pathlib import Path

def update_manifests(eks_dir, namespace, image_tag):
    """Update all YAML files in eks_dir with new namespace and image tags."""
    eks_path = Path(eks_dir)
    if not eks_path.exists():
        print(f"❌ Directory not found: {eks_dir}")
        sys.exit(1)
    
    updated_files = []
    for yaml_file in eks_path.glob("*.yaml"):
        try:
            with open(yaml_file, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Update image tags
            content = re.sub(
                r'ghcr\.io/soumantrivedi/ideaforge-ai/backend:.*',
                f'ghcr.io/soumantrivedi/ideaforge-ai/backend:{image_tag}',
                content
            )
            content = re.sub(
                r'ghcr\.io/soumantrivedi/ideaforge-ai/frontend:.*',
                f'ghcr.io/soumantrivedi/ideaforge-ai/frontend:{image_tag}',
                content
            )
            
            # Update namespace fields - replace any namespace value with the target namespace
            # This handles: namespace: ideaforge-ai, namespace: test-namespace, etc.
            content = re.sub(
                r'namespace:\s+[^\s#\n]+',
                f'namespace: {namespace}',
                content
            )
            
            # Update name field in Namespace resource metadata only
            # Match standalone "name:" values that are namespace names (not resource names)
            # Only replace if it's a known namespace pattern or ideaforge-ai
            known_namespaces = ['ideaforge-ai', 'test-namespace']
            for old_ns in known_namespaces:
                # Match "name: old_ns" at end of line (standalone, not part of longer name)
                content = re.sub(
                    rf'(\s+name:\s+){re.escape(old_ns)}(\s*#.*)?$',
                    f'\\1{namespace}\\2',
                    content,
                    flags=re.MULTILINE
                )
            
            if content != original_content:
                with open(yaml_file, 'w') as f:
                    f.write(content)
                updated_files.append(yaml_file.name)
        
        except Exception as e:
            print(f"⚠️  Error updating {yaml_file}: {e}")
            continue
    
    if updated_files:
        print(f"✅ Updated {len(updated_files)} files: {', '.join(updated_files)}")
    else:
        print("ℹ️  No files needed updating")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 update-eks-namespace.py <eks_dir> <namespace> <image_tag>")
        sys.exit(1)
    
    eks_dir = sys.argv[1]
    namespace = sys.argv[2]
    image_tag = sys.argv[3]
    
    update_manifests(eks_dir, namespace, image_tag)

