#!/bin/sh
# Creates the test database (with pgvector) alongside the main one.
# Runs only on the very first container start (empty data volume).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE DATABASE ${POSTGRES_TEST_DB:-shopsense_test};
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${POSTGRES_TEST_DB:-shopsense_test}" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
