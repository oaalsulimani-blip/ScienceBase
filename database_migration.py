# database_migration.py
import pandas as pd
import logging
from sqlalchemy import create_engine, text, inspect
from config_config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.db_engine = create_engine(Config.DATABASE_URL)
    
    def check_current_schema(self):
        """Check the current database schema"""
        try:
            inspector = inspect(self.db_engine)
            tables = inspector.get_table_names()
            
            logger.info("📊 Current Database Schema:")
            for table in tables:
                logger.info(f"  Table: {table}")
                columns = inspector.get_columns(table)
                for column in columns:
                    logger.info(f"    - {column['name']} ({column['type']})")
            
            return tables
        except Exception as e:
            logger.error(f"❌ Error checking schema: {str(e)}")
            return []
    
    def migrate_researchers_table(self):
        """Add missing columns to researchers table"""
        try:
            with self.db_engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Check if columns exist
                    inspector = inspect(self.db_engine)
                    existing_columns = [col['name'] for col in inspector.get_columns('researchers')]
                    
                    # Add orcid_valid column if it doesn't exist
                    if 'orcid_valid' not in existing_columns:
                        logger.info("➕ Adding 'orcid_valid' column to researchers table...")
                        conn.execute(text("ALTER TABLE researchers ADD COLUMN orcid_valid BOOLEAN DEFAULT FALSE"))
                    
                    # Add publications_count column if it doesn't exist
                    if 'publications_count' not in existing_columns:
                        logger.info("➕ Adding 'publications_count' column to researchers table...")
                        conn.execute(text("ALTER TABLE researchers ADD COLUMN publications_count INTEGER DEFAULT 0"))
                    
                    # Add email column if it doesn't exist (for backward compatibility)
                    if 'email' not in existing_columns:
                        logger.info("➕ Adding 'email' column to researchers table...")
                        conn.execute(text("ALTER TABLE researchers ADD COLUMN email TEXT DEFAULT ''"))
                    
                    trans.commit()
                    logger.info("✅ Successfully migrated researchers table")
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    raise e
                    
        except Exception as e:
            logger.error(f"❌ Error migrating researchers table: {str(e)}")
            return False
    
    def create_tables_if_not_exist(self):
        """Create all necessary tables if they don't exist"""
        try:
            with self.db_engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Create researchers table
                    conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS researchers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        orcid TEXT UNIQUE,
                        department TEXT,
                        college TEXT,
                        university TEXT,
                        email TEXT DEFAULT '',
                        orcid_valid BOOLEAN DEFAULT FALSE,
                        publications_count INTEGER DEFAULT 0,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """))
                    
                    # Create publications table
                    conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS publications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        researcher_id INTEGER,
                        title TEXT,
                        year INTEGER,
                        source TEXT,
                        citations INTEGER DEFAULT 0,
                        doi TEXT,
                        url TEXT,
                        journal TEXT,
                        data_source TEXT,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (researcher_id) REFERENCES researchers (id)
                    )
                    """))
                    
                    # Create metrics_snapshots table
                    conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS metrics_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        researcher_id INTEGER,
                        snapshot_date DATE,
                        total_publications INTEGER DEFAULT 0,
                        total_citations INTEGER DEFAULT 0,
                        wos_publications INTEGER DEFAULT 0,
                        wos_citations INTEGER DEFAULT 0,
                        scopus_publications INTEGER DEFAULT 0,
                        scopus_citations INTEGER DEFAULT 0,
                        pubmed_publications INTEGER DEFAULT 0,
                        pubmed_citations INTEGER DEFAULT 0,
                        other_publications INTEGER DEFAULT 0,
                        other_citations INTEGER DEFAULT 0,
                        FOREIGN KEY (researcher_id) REFERENCES researchers (id)
                    )
                    """))
                    
                    trans.commit()
                    logger.info("✅ Successfully created/verified all tables")
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    raise e
                    
        except Exception as e:
            logger.error(f"❌ Error creating tables: {str(e)}")
            return False
    
    def sync_orcid_data_to_database(self):
        """Sync ORCID data from Excel to database"""
        try:
            # Load corrected ORCID data
            orcid_df = pd.read_excel("data_ORCIDs_CORRECTED.xlsx")
            
            with self.db_engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Clear existing researchers
                    conn.execute(text("DELETE FROM researchers"))
                    
                    # Insert all researchers from corrected file
                    for _, row in orcid_df.iterrows():
                        insert_query = text("""
                        INSERT INTO researchers (name, orcid, department, college, university, email, orcid_valid, publications_count)
                        VALUES (:name, :orcid, :department, :college, :university, :email, :orcid_valid, :publications_count)
                        """)
                        conn.execute(insert_query, {
                            'name': row['name'],
                            'orcid': row['orcid'],
                            'department': row.get('department', ''),
                            'college': row.get('college', ''),
                            'university': row.get('university', ''),
                            'email': row.get('email', ''),
                            'orcid_valid': row.get('orcid_valid', False),
                            'publications_count': row.get('publications_count', 0)
                        })
                    
                    trans.commit()
                    logger.info(f"✅ Synced {len(orcid_df)} researchers to database")
                    return len(orcid_df)
                    
                except Exception as e:
                    trans.rollback()
                    raise e
                    
        except Exception as e:
            logger.error(f"❌ Error syncing ORCID data: {str(e)}")
            return 0
    
    def run_full_migration(self):
        """Run complete database migration"""
        logger.info("🔄 Starting full database migration...")
        
        # Step 1: Check current schema
        logger.info("📋 Step 1: Checking current schema...")
        self.check_current_schema()
        
        # Step 2: Create tables if they don't exist
        logger.info("📋 Step 2: Creating/verifying tables...")
        if not self.create_tables_if_not_exist():
            return False
        
        # Step 3: Migrate researchers table
        logger.info("📋 Step 3: Migrating researchers table...")
        if not self.migrate_researchers_table():
            return False
        
        # Step 4: Sync ORCID data
        logger.info("📋 Step 4: Syncing ORCID data...")
        count = self.sync_orcid_data_to_database()
        if count == 0:
            return False
        
        # Step 5: Verify migration
        logger.info("📋 Step 5: Verifying migration...")
        self.check_current_schema()
        
        logger.info("🎉 Database migration completed successfully!")
        return True

def main():
    migrator = DatabaseMigrator()
    
    print("🔄 DATABASE MIGRATION TOOL")
    print("=" * 50)
    print("This will update your database schema to work with the new dashboard")
    print("=" * 50)
    print("1. Run full migration (Recommended)")
    print("2. Check current schema only")
    print("3. Create tables only")
    print("4. Migrate researchers table only")
    print("5. Sync ORCID data only")
    
    choice = input("\nChoose option (1-5): ").strip()
    
    if choice == "1":
        success = migrator.run_full_migration()
        if success:
            print("\n✅ Migration completed! You can now run the safe auto-updater.")
        else:
            print("\n❌ Migration failed. Check the logs for details.")
    elif choice == "2":
        migrator.check_current_schema()
    elif choice == "3":
        migrator.create_tables_if_not_exist()
    elif choice == "4":
        migrator.migrate_researchers_table()
    elif choice == "5":
        migrator.sync_orcid_data_to_database()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()