#!/bin/sh
set -eu

secret_dir=/run/app-secrets
mkdir -p "$secret_dir"

generate_secret() {
    name=$1
    bytes=$2
    path="$secret_dir/$name"

    if [ ! -s "$path" ]; then
        umask 077
        python -c \
            'import base64, secrets, sys; print(base64.b64encode(secrets.token_bytes(int(sys.argv[1]))).decode())' \
            "$bytes" > "$path"
    fi
}

generate_secret encrypted-storage-key 32
generate_secret chainlit-auth-secret 32
generate_secret log-user-hash-salt 32

export ENCRYPTED_STORAGE_KEY="${ENCRYPTED_STORAGE_KEY:-$(cat "$secret_dir/encrypted-storage-key")}"
export CHAINLIT_AUTH_SECRET="${CHAINLIT_AUTH_SECRET:-$(cat "$secret_dir/chainlit-auth-secret")}"
export LOG_USER_HASH_SALT="${LOG_USER_HASH_SALT:-$(cat "$secret_dir/log-user-hash-salt")}"

exec "$@"
