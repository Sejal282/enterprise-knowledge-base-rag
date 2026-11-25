
from app.database import SessionLocal
from app.models import Document


db = SessionLocal()

try:
    # CREATE: Insert a document record
    document = Document(
        filename="employee_handbook.pdf",
        content_type="application/pdf",
        status="pending",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    print("Document created successfully!")
    print("Document ID:", document.id)

    # READ: Retrieve the document
    saved_document = (
        db.query(Document)
        .filter(Document.id == document.id)
        .first()
    )


    if saved_document:
        print("Document found!")
        print("Filename:", saved_document.filename)
        print("Status:", saved_document.status)

        # UPDATE: Change the document status
        saved_document.status = "completed"
        db.commit()
        db.refresh(saved_document)

        print("Updated status:", saved_document.status)

        # DELETE: Remove this test record
        db.delete(saved_document)
        db.commit()

        print("Test document deleted successfully!")


except Exception as e:
    db.rollback()
    print("Database operation failed:", e)

finally:
    db.close()
