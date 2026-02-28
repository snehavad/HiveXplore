"""
Schema Visualization Generator for HiveBuzz

This script generates a visual representation of the SQLite database schema.
Requires:
    - pydot (pip install pydot)
    - graphviz (https://graphviz.org/download/)
"""

import logging
import os
import sqlite3
from pathlib import Path

import pydot

import database as db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output file paths
OUTPUT_DIR = Path("./docs")
OUTPUT_FILE = OUTPUT_DIR / "schema.png"


def get_table_info(conn):
    """Get all tables and their columns"""
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = [row[0] for row in cursor.fetchall()]

    table_info = {}
    foreign_keys = {}

    # Get columns and primary keys for each table
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        # Format: id, name, type, notnull, default_value, primary_key
        table_info[table] = columns

        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()

        if fks:
            foreign_keys[table] = fks

    return table_info, foreign_keys


def generate_schema_diagram(table_info, foreign_keys):
    """Generate a graphviz diagram of the schema"""
    graph = pydot.Dot("HiveBuzz Database Schema", graph_type="digraph", rankdir="LR")

    # Add tables as nodes
    for table_name, columns in table_info.items():
        label = f"{table_name}\\n"

        # Add columns to table label
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, is_pk = col

            # Format column with data type and constraints
            column_str = f"{col_name} : {col_type}"

            # Add primary key indicator
            if is_pk:
                column_str = f"<b>{column_str} (PK)</b>"

            # Add not null constraint
            if not_null:
                column_str += " NN"

            label += f"{column_str}\\n"

        # Create the table node
        table_node = pydot.Node(
            table_name,
            label=label,
            shape="box",
            style="rounded,filled",
            fillcolor="#f5f5f5",
            fontname="Arial",
        )
        graph.add_node(table_node)

    # Add foreign key relations as edges
    for table_name, fks in foreign_keys.items():
        for fk in fks:
            # Format: id, seq, table, from, to, on_update, on_delete, match
            _, _, ref_table, from_col, to_col, _, _, _ = fk

            edge = pydot.Edge(
                table_name,
                ref_table,
                label=f"  {from_col} -> {to_col}  ",
                fontsize=10,
                fontname="Arial",
                color="#666666",
            )
            graph.add_edge(edge)

    return graph


def main():
    """Main function"""
    try:
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(exist_ok=True)

        # Connect to database
        conn = db.get_db_connection()

        # Get table information
        tables, foreign_keys = get_table_info(conn)

        # Generate and save diagram
        graph = generate_schema_diagram(tables, foreign_keys)
        graph.write(str(OUTPUT_FILE), format="png")

        logger.info(f"Schema diagram generated at {OUTPUT_FILE}")

        # Close connection
        conn.close()

    except ImportError:
        logger.error(
            "This script requires pydot and graphviz. Install with: pip install pydot"
        )
    except Exception as e:
        logger.error(f"Error generating schema diagram: {e}")


if __name__ == "__main__":
    main()
