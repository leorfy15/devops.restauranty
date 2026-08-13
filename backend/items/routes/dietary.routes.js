const express = require('express');
const router = express.Router();

const Dietary = require('../models/dietary.model');
const fileUploader = require('../config/cloudinary.config');


// ========================================
// GET ALL DIETARY CATEGORIES
// ========================================
router.get("/", (req, res) => {

    Dietary.find()
        .then(dietary => {
            res.json(dietary);
        })
        .catch(err => {
            console.error("ERROR GETTING DIETARIES:", err);

            res.status(400).json({
                message: err.message
            });
        });

});


// ========================================
// GET ONE DIETARY CATEGORY
// ========================================
router.get("/:id", (req, res) => {

    const id = req.params.id;

    Dietary.findById(id)
        .then(dietary => {

            if (!dietary) {
                return res.status(404).json({
                    message: "Dietary category not found"
                });
            }

            res.json(dietary);
        })
        .catch(err => {
            console.error("ERROR GETTING DIETARY:", err);

            res.status(400).json({
                message: err.message
            });
        });

});


// ========================================
// CREATE DIETARY CATEGORY
// ========================================
router.post("/", fileUploader.single("imagem"), (req, res) => {

    const dietary = req.body;

    console.log("BODY RECEIVED:", dietary);

    // If an image was uploaded to Cloudinary,
    // add its URL to the object
    if (req.file) {
        dietary.imagem = req.file.path;
    }

    Dietary.create(dietary)
        .then(newDietary => {

            console.log("DIETARY CREATED:", newDietary);

            res.status(201).json(newDietary);

        })
        .catch(err => {

            console.error("ERROR CREATING DIETARY:");
            console.error(err);

            res.status(400).json({
                message: err.message,
                errors: err.errors
            });

        });

});


// ========================================
// UPDATE DIETARY CATEGORY
// ========================================
router.put("/:id", fileUploader.single("imagem"), (req, res) => {

    const id = req.params.id;
    const dietary = req.body;

    // If a new image was uploaded
    if (req.file) {
        dietary.imagem = req.file.path;
    }

    Dietary.findByIdAndUpdate(
        id,
        dietary,
        {
            new: true,
            runValidators: true
        }
    )
        .then(updatedDietary => {

            if (!updatedDietary) {
                return res.status(404).json({
                    message: "Dietary category not found"
                });
            }

            console.log("DIETARY UPDATED:", updatedDietary);

            res.json(updatedDietary);

        })
        .catch(err => {

            console.error("ERROR UPDATING DIETARY:", err);

            res.status(400).json({
                message: err.message,
                errors: err.errors
            });

        });

});


// ========================================
// DELETE DIETARY CATEGORY
// ========================================
router.delete("/:id", (req, res) => {

    const id = req.params.id;

    Dietary.findByIdAndDelete(id)
        .then(dietaryDeleted => {

            if (!dietaryDeleted) {
                return res.status(404).json({
                    message: "Dietary category not found"
                });
            }

            console.log("DIETARY DELETED:", dietaryDeleted);

            res.json({
                message: "Dietary deleted successfully",
                dietaryDeleted: dietaryDeleted
            });

        })
        .catch(err => {

            console.error("ERROR DELETING DIETARY:", err);

            res.status(400).json({
                message: err.message
            });

        });

});


module.exports = router;