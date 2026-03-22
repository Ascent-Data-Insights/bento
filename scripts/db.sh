#!/bin/bash
# Connect to the routing database via lazysql
PGPASSWORD=routing lazysql "postgres://routing:routing@localhost:5432/routing?sslmode=disable"
