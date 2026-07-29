// Runs once, on first boot of an empty data volume.
//
// Creates a least-privilege application user. The 2022 server connected to
// MongoDB Atlas as `admin`, so an application-level bug had full cluster
// authority. This user can only read and write the one application database.

const dbName = process.env.FZIP_MONGO_DB || 'fzip';
const appUser = process.env.MONGO_APP_USERNAME;
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!appUser || !appPassword) {
    throw new Error(
        'MONGO_APP_USERNAME and MONGO_APP_PASSWORD must be set. ' +
        'Copy .env.example to .env and fill them in.'
    );
}

const appDb = db.getSiblingDB(dbName);

appDb.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [{ role: 'readWrite', db: dbName }],
});

print(`created least-privilege user '${appUser}' with readWrite on '${dbName}'`);
