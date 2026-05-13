from fastapi import FastAPI, HTTPException
from database import get_connection
from models import RentalCreate, RentalUpdate
import requests
from fastapi import HTTPException
from logging_config import get_logger

logger = get_logger("rental-service")
app = FastAPI()

SCHEMA_NAME = "UladzislauMikhayevich"
TABLE_NAME = "rentals"
SUPPLY_SERVICE_URL = "http://supply-service:8000"
ALERT_SERVICE_URL = "http://alert-service:8000"


@app.get("/")
def health_check():
    logger.info("Health check called")
    return {"message": "Rental API is running"}


@app.get("/setup")
def setup_database():
    logger.info(f"Setup database")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            IF NOT EXISTS (
                SELECT * FROM sys.schemas
                WHERE name = '{SCHEMA_NAME}'
            )
            BEGIN
                EXEC('CREATE SCHEMA [{SCHEMA_NAME}]')
            END
            """
        )

        cursor.execute(
            f"""
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
            """
        )

        conn.commit()

        message = (
            f"Schema [{SCHEMA_NAME}] and table "
            f"[{TABLE_NAME}] created successfully"
        )

        return {"message": message}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.post("/rentals")
def create_rental(rental: RentalCreate):
    logger.info(f"Creating rental user_id={rental.user_id}, item_id={rental.item_id}")
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

        logger.info(f"Rental created with id={inserted_id}")
        return {
            "message": "Rental created successfully",
            "id": inserted_id,
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.get("/rentals/{id}")
def get_rental(id: int):
    logger.info(f"Get rental with id={id}")
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
            raise HTTPException(status_code=404,
                                detail="Rental not found")

        columns = [column[0] for column in cursor.description]

        return dict(zip(columns, row))

    finally:
        cursor.close()
        conn.close()


@app.get("/rentals/user/{user_id}")
def get_user_rentals(user_id: int):
    logger.info(f"Get user rentals with id={id}")
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


@app.put("/rentals/{id}")
def update_rental(id: int, rental: RentalUpdate):
    logger.info(f"Put rental with id={id}")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT id
            FROM [{SCHEMA_NAME}].[{TABLE_NAME}]
            WHERE id = ?
            """,
            (id,),
        )

        if not cursor.fetchone():
            raise HTTPException(status_code=404,
                                detail="Rental not found")

        update_fields = []
        values = []

        rental_data = rental.dict(exclude_unset=True)

        for key, value in rental_data.items():
            update_fields.append(f"{key} = ?")
            values.append(value)

        if not update_fields:
            raise HTTPException(status_code=400,
                                detail="No fields to update")

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


@app.delete("/rentals/{id}")
def delete_rental(id: int):
    logger.info(f"Delete rental with id={id}")
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
            raise HTTPException(status_code=404,
                                detail="Rental not found")

        conn.commit()

        return {"message": "Rental deleted successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@app.post("/rentals/{id}/calculate")
def calculate_rental_price(id: int):
    logger.info(f"Calculate rental with id={id}")
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
            raise HTTPException(status_code=404,
                                detail="Rental not found")

        start_date, end_date = row

        rental_days = (end_date - start_date).days
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


@app.post("/rentals/full")
def create_full_rental(rental: RentalCreate):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # 1. Create rental
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
                "pending",
                rental.total_price,
            ),
        )

        rental_id = cursor.fetchone()[0]

        conn.commit()

        # 2. Reserve item in supply-service
        reserve_response = requests.post(
            f"{SUPPLY_SERVICE_URL}/items/{rental.item_id}/reserve",
            json={
                "rental_id": rental_id,
                "reserved_count": 1,
            },
        )

        if reserve_response.status_code != 200:

            cursor.execute(
                f"""
                UPDATE [{SCHEMA_NAME}].[{TABLE_NAME}]
                SET status = 'rejected'
                WHERE id = ?
                """,
                (rental_id,),
            )

            conn.commit()

            raise HTTPException(
                status_code=400,
                detail="Item reservation failed",
            )

        # 3. Update rental status
        cursor.execute(
            f"""
            UPDATE [{SCHEMA_NAME}].[{TABLE_NAME}]
            SET status = 'approved'
            WHERE id = ?
            """,
            (rental_id,),
        )

        conn.commit()

        # 4. Create feedback request
        requests.post(
            f"{ALERT_SERVICE_URL}/feedback/request",
            json={
                "user_id": rental.user_id,
                "item_id": rental.item_id,
                "rating": 1,
                "comment": "THX!!!!" 
            },
        )

        return {
            "message": "Rental completed successfully",
            "rental_id": rental_id,
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:
        cursor.close()
        conn.close()
