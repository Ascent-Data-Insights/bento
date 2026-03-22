"""Seed the database with demo data for Green Acres Landscaping."""

import sys
from datetime import date

from backend.db.models import Base, Job, Location, Profile, Resource, Tenant, Vehicle
from backend.db.session import SessionLocal, engine


def seed(target_date: date | None = None) -> None:
    seed_date = target_date or date.today()

    # Create tables
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(Tenant).filter(Tenant.name == "Green Acres Landscaping").first()
        if existing:
            print("Demo data already exists. Skipping.")
            return

        # Create tenant
        tenant = Tenant(name="Green Acres Landscaping", industry="landscaping")
        db.add(tenant)
        db.flush()

        # Create locations (matching frontend demo data coordinates)
        depot = Location(
            tenant_id=tenant.id,
            name="Green Acres HQ",
            latitude=39.2361,
            longitude=-84.3816,
            service_time=0,
        )
        johnson = Location(
            tenant_id=tenant.id,
            name="Johnson Residence",
            latitude=39.1390,
            longitude=-84.4440,
            service_time=45,
        )
        oak_hills = Location(
            tenant_id=tenant.id,
            name="Oak Hills Community Center",
            latitude=39.1580,
            longitude=-84.6050,
            service_time=90,
        )
        riverside = Location(
            tenant_id=tenant.id,
            name="Riverside Park",
            latitude=39.0850,
            longitude=-84.3700,
            service_time=60,
        )
        summit = Location(
            tenant_id=tenant.id,
            name="Summit Ave Property",
            latitude=39.1090,
            longitude=-84.4970,
            service_time=30,
        )
        crestview = Location(
            tenant_id=tenant.id,
            name="Crestview Estates",
            latitude=39.0540,
            longitude=-84.6600,
            service_time=75,
        )

        locations = [depot, johnson, oak_hills, riverside, summit, crestview]
        db.add_all(locations)
        db.flush()

        # Create profile
        profile = Profile(
            tenant_id=tenant.id,
            name="Default",
            origin_model="single_depot",
            fleet_composition="heterogeneous",
            objective={"distance": 1.0},
            modules=[
                {"key": "time_windows", "enabled": True, "params": {}},
            ],
            is_active=True,
        )
        db.add(profile)

        # Create vehicles
        truck_alpha = Vehicle(
            tenant_id=tenant.id,
            name="Truck Alpha",
            start_location_id=depot.id,
            end_location_id=depot.id,
            compartments=[
                {"type": "cab", "capacity": {"seats": 3}},
                {"type": "bed", "capacity": {"weight": 600, "volume": 40}},
            ],
        )
        truck_bravo = Vehicle(
            tenant_id=tenant.id,
            name="Truck Bravo",
            start_location_id=depot.id,
            end_location_id=depot.id,
            compartments=[
                {"type": "cab", "capacity": {"seats": 2}},
                {"type": "bed", "capacity": {"weight": 400, "volume": 25}},
            ],
        )
        truck_charlie = Vehicle(
            tenant_id=tenant.id,
            name="Truck Charlie",
            start_location_id=depot.id,
            end_location_id=depot.id,
            compartments=[
                {"type": "cab", "capacity": {"seats": 3}},
                {"type": "bed", "capacity": {"weight": 500, "volume": 35}},
                {"type": "trailer", "capacity": {"weight": 800, "volume": 60}},
            ],
        )
        db.add_all([truck_alpha, truck_bravo, truck_charlie])

        # Create resources — workers
        workers = []
        for name in ["Mike", "Dave", "Sarah", "Tom", "Lisa"]:
            w = Resource(
                tenant_id=tenant.id,
                name=name,
                pickup_location_id=depot.id,
                compartment_types=["cab"],
                capacity_consumption={"seats": 1},
                stays_with_vehicle=True,
                attributes={"skill": "mower_operator"},
            )
            workers.append(w)
        db.add_all(workers)

        # Create resources — mowers
        mowers = []
        for i in range(1, 4):
            m = Resource(
                tenant_id=tenant.id,
                name=f"Mower #{i}",
                pickup_location_id=depot.id,
                compartment_types=["bed", "trailer"],
                capacity_consumption={"weight": 80, "volume": 5},
                stays_with_vehicle=True,
                attributes={"type": "mower"},
            )
            mowers.append(m)
        db.add_all(mowers)

        # Create resources — mulch (consumed)
        mulch_oak = Resource(
            tenant_id=tenant.id,
            name="Mulch (Oak Hills)",
            pickup_location_id=depot.id,
            dropoff_location_id=oak_hills.id,
            compartment_types=["bed", "trailer"],
            capacity_consumption={"weight": 40, "volume": 2},
            quantity=5,
            stays_with_vehicle=False,
        )
        mulch_crestview = Resource(
            tenant_id=tenant.id,
            name="Mulch (Crestview)",
            pickup_location_id=depot.id,
            dropoff_location_id=crestview.id,
            compartment_types=["bed", "trailer"],
            capacity_consumption={"weight": 40, "volume": 2},
            quantity=3,
            stays_with_vehicle=False,
        )
        db.add_all([mulch_oak, mulch_crestview])

        # Create jobs for seed_date
        jobs_data = [
            (
                johnson,
                "Mow Johnson Residence",
                "Weekly mow & edge, front and back yard",
                [
                    {"attributes": {"skill": "mower_operator"}, "quantity": 1},
                    {"attributes": {"type": "mower"}, "quantity": 1},
                ],
                480.0,
                600.0,
            ),
            (
                oak_hills,
                "Oak Hills Grounds Maintenance",
                "Full grounds maintenance, mulch beds and common areas",
                [
                    {"attributes": {"skill": "mower_operator"}, "quantity": 1},
                    {"attributes": {"type": "mower"}, "quantity": 1},
                ],
                480.0,
                600.0,
            ),
            (
                riverside,
                "Mow Riverside Park",
                "Bi-weekly mow, trim along walking paths",
                [
                    {"attributes": {"skill": "mower_operator"}, "quantity": 1},
                    {"attributes": {"type": "mower"}, "quantity": 1},
                ],
                600.0,
                720.0,
            ),
            (
                summit,
                "Summit Ave Quote",
                "Quote for new landscaping design",
                [
                    {"attributes": {"skill": "mower_operator"}, "quantity": 1},
                ],
                540.0,
                660.0,
            ),
            (
                crestview,
                "Crestview Spring Cleanup",
                "Spring cleanup, mowing, and mulch delivery",
                [
                    {"attributes": {"skill": "mower_operator"}, "quantity": 1},
                    {"attributes": {"type": "mower"}, "quantity": 1},
                ],
                600.0,
                840.0,
            ),
        ]
        for loc, name, desc, reqs, tw_e, tw_l in jobs_data:
            job = Job(
                tenant_id=tenant.id,
                location_id=loc.id,
                date=seed_date,
                name=name,
                description=desc,
                service_time=loc.service_time,
                required_resources=reqs,
                time_window_earliest=tw_e,
                time_window_latest=tw_l,
            )
            db.add(job)

        db.commit()
        print(f"Seeded demo data for Green Acres Landscaping (tenant_id: {tenant.id})")
        print(f"  - 6 locations, 3 vehicles, 10 resources, 5 jobs for {seed_date}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Accept optional date argument: uv run python -m backend.db.seed 2026-03-25
    target = None
    if len(sys.argv) > 1:
        target = date.fromisoformat(sys.argv[1])
    seed(target)
