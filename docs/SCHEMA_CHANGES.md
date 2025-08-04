# Schema Changes Guide

This guide explains how to handle database schema changes in development and production.

## 🔄 Types of Schema Changes

### **1. New Tables** ✅ **Handled Automatically**
```python
# Add new model
class Pet(Base):
    __tablename__ = "pets"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
```

**What happens:** ✅ New table created automatically

### **2. New Columns** ✅ **Now Handled Automatically**
```python
# Add field to existing model
class User(Base):
    # ... existing fields
    bio = Column(String, nullable=True)  # NEW FIELD
```

**What happens:** ✅ New column added to existing table

### **3. Column Changes** ⚠️ **Requires Migration**
```python
# Change column type or constraints
class User(Base):
    # ... existing fields
    email = Column(String(500), nullable=False)  # Changed length
```

**What happens:** ⚠️ Requires Alembic migration

## 🛠️ Development Workflow

### **Automatic Schema Updates**
```bash
# Smart development script (recommended)
./scripts/dev.sh
```

**What it does:**
1. ✅ Detects new tables → Creates them
2. ✅ Detects new columns → Adds them to existing tables
3. ✅ Preserves all existing data
4. ✅ Starts server

### **Manual Schema Management**
```bash
# Check current schema status
python scripts/schema_manager.py --status

# Apply schema changes
python scripts/schema_manager.py --update

# Force recreate (destructive)
python scripts/schema_manager.py --force
```

## 📊 Schema Change Examples

### **Example 1: Adding New Field to User**

#### **Before:**
```python
class User(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
```

#### **After:**
```python
class User(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    bio = Column(String, nullable=True)  # NEW FIELD
```

#### **What Happens:**
```bash
./scripts/dev.sh
```

**Output:**
```
🔍 Analyzing schema changes...
🔧 Adding columns to users: bio
✅ Added column: users.bio
✅ Schema update completed successfully
```

**Result:**
- ✅ Existing users keep all their data
- ✅ New `bio` column added (NULL for existing users)
- ✅ New users can have bio field

### **Example 2: Adding New Pet Model**

#### **Create Model:**
```python
# app/models/pet.py
class Pet(Base):
    __tablename__ = "pets"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
```

#### **Update Imports:**
```python
# app/models/__init__.py
from .user import User, UserRole
from .pet import Pet  # Add this
```

#### **Run Development:**
```bash
./scripts/dev.sh
```

**Output:**
```
🔍 Analyzing schema changes...
🆕 Creating new tables: pets
✅ Created table: pets
✅ Schema update completed successfully
```

## 🏭 Production Schema Changes

### **Production Uses Alembic Migrations**

#### **Step 1: Create Migration**
```bash
# After changing models
alembic revision --autogenerate -m "Add bio field to User model"
```

#### **Step 2: Review Migration**
```python
# alembic/versions/xxx_add_bio_field.py
def upgrade() -> None:
    op.add_column('users', sa.Column('bio', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'bio')
```

#### **Step 3: Apply Migration**
```bash
# Production deployment
alembic upgrade head
```

## 📋 Schema Change Matrix

| Change Type | Development | Production | Data Safe |
|-------------|-------------|------------|-----------|
| **New Table** | ✅ Auto | 🔧 Migration | ✅ Yes |
| **New Column** | ✅ Auto | 🔧 Migration | ✅ Yes |
| **Column Type** | ⚠️ Migration | 🔧 Migration | ⚠️ Depends |
| **Drop Column** | ⚠️ Migration | 🔧 Migration | ❌ No |
| **Rename Column** | ⚠️ Migration | 🔧 Migration | ⚠️ Depends |

## 🔍 Troubleshooting

### **"Column already exists" Error**
```bash
# Check current schema
python scripts/schema_manager.py --status

# Should show column already exists
```

### **"Missing column" in Application**
```bash
# Update schema
python scripts/schema_manager.py --update

# Or restart dev server
./scripts/dev.sh
```

### **Schema Conflicts**
```bash
# Check what's different
python scripts/schema_manager.py --status

# Force recreate if needed (loses data!)
python scripts/schema_manager.py --force
```

### **Production Schema Issues**
```bash
# Never use dev scripts in production!
# Use migrations instead:
alembic upgrade head
```

## 🎯 Best Practices

### **Development**
- ✅ Use `./scripts/dev.sh` for daily development
- ✅ Add new fields as `nullable=True` initially
- ✅ Use `python scripts/schema_manager.py --status` to check schema
- ✅ Test schema changes before committing

### **Production**
- ✅ Always use Alembic migrations
- ✅ Test migrations in staging first
- ✅ Review auto-generated migrations
- ✅ Have database backups before migrations

### **Model Changes**
- ✅ Add new fields as optional (`nullable=True`)
- ✅ Use sensible defaults for new fields
- ✅ Consider backward compatibility
- ✅ Document breaking changes

## 🚀 Common Scenarios

### **Scenario 1: Add Optional Field**
```python
# Safe - will be added automatically
bio = Column(String, nullable=True)
```

### **Scenario 2: Add Required Field with Default**
```python
# Safe - will be added with default value
status = Column(String, nullable=False, default="active")
```

### **Scenario 3: Add Required Field (No Default)**
```python
# Requires migration - existing records need values
required_field = Column(String, nullable=False)
```

### **Scenario 4: Change Column Type**
```python
# Requires migration - data conversion needed
# Before: age = Column(String)
# After:  age = Column(Integer)
```

## ✅ Summary

The schema management system now handles:

- 🆕 **New Tables**: Created automatically
- 🔧 **New Columns**: Added automatically to existing tables
- 🛡️ **Data Safety**: Never loses existing data
- 🔄 **Smart Detection**: Compares models vs database
- 🏭 **Production Ready**: Uses proper migrations

Your development workflow is now seamless for most schema changes! 🎯