const cloudinary = require("cloudinary").v2;
const multer = require("multer");

cloudinary.config({
    cloud_name: process.env.CLOUD_NAME,
    api_key: process.env.CLOUD_API_KEY,
    api_secret: process.env.CLOUD_API_SECRET
});

const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: 5 * 1024 * 1024
    }
});

function single(fieldName) {
    return (req, res, next) => {
        upload.single(fieldName)(req, res, (err) => {
            if (err) {
                return next(err);
            }

            if (!req.file) {
                return next();
            }

            const stream = cloudinary.uploader.upload_stream(
                {
                    folder: "restaurant",
                    resource_type: "image",
                    allowed_formats: ["png", "jpeg", "jpg"]
                },
                (error, result) => {
                    if (error) {
                        return next(error);
                    }

                    req.file.path = result.secure_url;
                    req.file.filename = result.public_id;

                    next();
                }
            );

            stream.end(req.file.buffer);
        });
    };
}

module.exports = {
    single
};