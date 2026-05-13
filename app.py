from fastapi import FastAPI, HTTPException
from database import get_connection
from models import RentalCreate, RentalUpdate

app = FastAPI()

SCHEMA_NAME = "UladzislauMikhayevich"
TABLE_NAME = "rentals"


@app.get("/")
def health_check():
    return {"message": "Rental API is running"}


# TEMP endpoint to create schema + table
@app.get("/setup")
def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Create schema if not exists
        cursor.execute(f"""
        IF NOT EXISTS (
            SELECT * FROM sys.schemas WHERE name = '{SCHEMA_NAME}'
        )
        BEGIN
            EXEC('CREATE SCHEMA [{SCHEMA_NAME}]')
        END
        """)

        # Create table if not exists
        cursor.execute(f"""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{SCHEMA_NAME}'
            AND TABLE_NAME = '{TABLE_NAME}'
        )
        BEGIN
            CREATE TABLE [{SCHEMA_NAME}].[{TABLE_NAME}] (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                item_id INT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status NVARCHAR(50) NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                created_at DATETIME2 DEFAULT GETDATE()
            )
        END
        """)

        conn.commit()

        return {
            "message": f"Schema [{SCHEMA_NAME}] and table [{TABLE_NAME}] created successfully"
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


# POST /rentals
@app.post("/rentals")
def create_rental(rental: RentalCreate):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        INSERT INTO [{SCHEMA_NAME}].[{TABLE_NAME}]
        (
            user_id,
            item_id,
            start_date,
            end_date,
            status,
            total_price
        )
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                rental.user_id,
                rental.item_id,
                rental.start_date,
                rental.end_date,
                rental.status,
                rental.total_price,
            ),
        )

        inserted_id = cursor.fetchone()[0]

        conn.commit()

        return {"message": "Rental created successfully", "id": inserted_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


# GET /rentals/{id}
@app.get("/rentals/{id}")
def get_rental(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        SELECT *
        FROM [{SCHEMA_NAME}].[{TABLE_NAME}]
        WHERE id = ?
        """,
            (id,),
        )

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Rental not found")

        columns = [column[0] for column in cursor.description]

        return dict(zip(columns, row))

    finally:
        cursor.close()
        conn.close()


# GET /rentals/user/{userId}
@app.get("/rentals/user/{user_id}")
def get_user_rentals(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        SELECT *
        FROM [{SCHEMA_NAME}].[{TABLE_NAME}]
        WHERE user_id = ?
        """,
            (user_id,),
        )

        rows = cursor.fetchall()

        columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row)) for row in rows]

    finally:
        cursor.close()
        conn.close()


# PUT /rentals/{id}
@app.put("/rentals/{id}")
def update_rental(id: int, rental: RentalUpdate):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if exists
        cursor.execute(
            f"""
        SELECT id
        FROM [{SCHEMA_NAME}].[{TABLE_NAME}]
        WHERE id = ?
        """,
            (id,),
        )

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Rental not found")

        update_fields = []
        values = []

        rental_data = rental.dict(exclude_unset=True)

        for key, value in rental_data.items():
            update_fields.append(f"{key} = ?")
            values.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(id)

        query = f"""
        UPDATE [{SCHEMA_NAME}].[{TABLE_NAME}]
        SET {", ".join(update_fields)}
        WHERE id = ?
        """

        cursor.execute(query, values)

        conn.commit()

        return {"message": "Rental updated successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


# DELETE /rentals/{id}
@app.delete("/rentals/{id}")
def delete_rental(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        DELETE FROM [{SCHEMA_NAME}].[{TABLE_NAME}]
        WHERE id = ?
        """,
            (id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rental not found")

        conn.commit()

        return {"message": "Rental deleted successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


# POST /rentals/{id}/calculate
@app.post("/rentals/{id}/calculate")
def calculate_rental_price(id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        SELECT start_date, end_date
        FROM [{SCHEMA_NAME}].[{TABLE_NAME}]
        WHERE id = ?
        """,
            (id,),
        )

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Rental not found")

        start_date, end_date = row

        rental_days = (end_date - start_date).days

        # Example pricing logic
        daily_rate = 25

        calculated_price = rental_days * daily_rate

        cursor.execute(
            f"""
        UPDATE [{SCHEMA_NAME}].[{TABLE_NAME}]
        SET total_price = ?
        WHERE id = ?
        """,
            (calculated_price, id),
        )

        conn.commit()

        return {
            "rental_days": rental_days,
            "daily_rate": daily_rate,
            "calculated_price": calculated_price,
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
