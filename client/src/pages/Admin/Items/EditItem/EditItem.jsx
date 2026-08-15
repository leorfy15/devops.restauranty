import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function EditItem() {
    const [item, setItem] = useState("");
    const [name, setName] = useState("");
    const [price, setPrice] = useState("");
    const [description, setDescription] = useState("");
    const [image, setImage] = useState("");
    const [dietaryInformation, setDietaryInformation] = useState([""]);
    const [availability, setAvailability] = useState("");
    const [errorMessage, setErrorMessage] = useState(undefined);
    const [dietaryOptions, setDietaryOptions] = useState([]);
    const [file, setFile] = useState(null);
    const [previewSrc, setPreviewSrc] = useState("");
    const [showSelectDietary, setShowSelectDietary] = useState(false);
    const [selectCount, setSelectCount] = useState(1);

    const { itemId } = useParams();

    const navigate = useNavigate();
    useEffect(() => {
        axios.get(`${url}/api/items/items/${itemId}`).then((response) => {
            setItem(response.data);
            setName(response.data.name);
            setPrice(response.data.price);
            setDescription(response.data.description);
            setAvailability(response.data.availability);
            setDietaryInformation(response.data.dietaryInformation || [""]);
            setImage(response.data.image);
            setPreviewSrc(response.data.image); // Set the previewSrc to the existing image URL
            console.log(response.data);
        });
    }, [itemId]);
    useEffect(() => {
        // Fetch dietary information options from the database
        axios
            .get(`${url}/items/dietary`)
            .then((response) => {
                setDietaryOptions(response.data);
            })
            .catch((error) => {
                console.error(error);
            });
    }, []);

    const handleDescription = (e) => setDescription(e.target.value);
    const handleName = (e) => setName(e.target.value);
    const handlePrice = (e) => {
        const inputPrice = e.target.value;
        // Remove non-digit characters from the input
        const sanitizedPrice = inputPrice.replace(/\D/g, "");
        setPrice(sanitizedPrice);
    };

    const handleDietaryInfo = (e, index) => {
        const updatedDietaryInfo = [...dietaryInformation];
        updatedDietaryInfo[index] = e.target.value;
        setDietaryInformation(updatedDietaryInfo);
    };

    const handleAddDietary = () => {
        setDietaryInformation((prevDietary) => [...prevDietary, ""]);
        setSelectCount((prevCount) => prevCount + 1);
    };

    const handleRemoveDietary = (index) => {
        setDietaryInformation((prevDietary) =>
            prevDietary.filter((_, i) => i !== index)
        );
        setSelectCount((prevCount) => prevCount - 1);
    };

    const handleAvailability = (e) => {
        console.log(e.target.value);
        setAvailability(e.target.value);
    };

    const onFileChange = (event) => {
        setFile(event.target.files[0]);

        // Show preview
        const fileReader = new FileReader();
        fileReader.readAsDataURL(event.target.files[0]);
        fileReader.onloadend = () => {
            setPreviewSrc(fileReader.result);
        };
    };

    const handleDietarySwitch = () => {
        if (Array.isArray(item.dietaryInformation)) {
            setSelectCount(item.dietaryInformation.length);
        } else {
            setSelectCount(1);
        }
        setShowSelectDietary(true);
    };

    const ItemhandleSubmit = (e) => {
        e.preventDefault();
        if (
            !name ||
            !price ||
            !availability ||
            !description ||
            !dietaryInformation
        ) {
            setErrorMessage("All fields must be filled.");
            return;
        }

        // Create an object representing the request body
        const formData = new FormData();
        formData.append("name", name);
        formData.append("price", price);
        formData.append("availability", availability);
        formData.append("description", description);
        for (let i = 0; i < dietaryInformation.length; i++) {
            formData.append("dietaryInformation[]", dietaryInformation[i]);
        }
        formData.append("imagem", file);

        axios
            .put(`${url}/api/items/items/${item._id}`, formData)
            .then((response) => {
                if (response.status === 200) {
                    console.log(response.data);
                }
                navigate("/items");
            })
            .catch((error) => {
                console.error(error);
                const errorDescription = error.response.data.message;
                setErrorMessage(errorDescription);
            });
    };

    return (
        <div className="main">
            <div>
                <h1>Edit Item {item.name}</h1>
                <div className="inputwrap w-[700px]">
                    <form onSubmit={ItemhandleSubmit}>
                        <div className="mt-2">
                            <input
                                className="forms m-4"
                                type="text"
                                name="name"
                                value={name}
                                placeholder="Item Name"
                                onChange={handleName}
                            />
                        </div>
                        <div>
                            <input
                                className="forms m-4"
                                type="text"
                                name="price"
                                value={price}
                                placeholder="Price"
                                onChange={handlePrice}
                            />
                        </div>
                        <div>
                            <textarea
                                className="forms m-4"
                                name="description"
                                value={description}
                                placeholder="Description"
                                onChange={handleDescription}
                            />
                        </div>
                        <div>
                            <input
                                className="forms m-4"
                                type="file"
                                name="imagem"
                                accept=".jpg,.jpeg,.png"
                                onChange={onFileChange}
                            />
                        </div>
                        <div className="main">
                            {previewSrc && <img src={previewSrc} width={400} className="images" alt="Preview" />}
                        </div>
                        <div>
                            <input type="radio" name="availability" id="available" value="true" onChange={handleAvailability} /><label className="m-2" htmlFor="available" >Available</label>
                            <input type="radio" name="availability" id="notavailable" value="false" onChange={handleAvailability} /><label className="m-2" htmlFor="notavailable">Unavailable</label>
                        </div>
                        <div>
                            {item.dietaryInformation && !showSelectDietary && (
                                <>
                                    {Array.isArray(item.dietaryInformation) ? (
                                        item.dietaryInformation.map((dietaryInfo, index) => (
                                            <p key={index}>
                                                Category: {dietaryInfo}
                                                <button className="button" onClick={handleDietarySwitch}>Change</button>
                                            </p>
                                        ))
                                    ) : (
                                        <p>
                                            Category: {item.dietaryInformation}
                                            <button onClick={handleDietarySwitch}>Change</button>
                                        </p>
                                    )}
                                </>
                            )}

                            {showSelectDietary && (
                                <div>

                                    {Array.from({ length: selectCount }, (_, index) => (
                                        <div key={index}>
                                            <label>Category {index + 1}:</label>
                                            <select
                                                className="forms m-4"
                                                name={`dietaryinfo${index}`}
                                                value={dietaryInformation[index] || ""}
                                                onChange={(e) => handleDietaryInfo(e, index)}
                                            >
                                                <option value="" disabled>Select Category</option>
                                                {dietaryOptions.map((option) => (
                                                    <option key={option.id} value={option.name}>
                                                        {option.name} - {option.description}
                                                    </option>
                                                ))}
                                            </select>
                                            {index == 0 && (
                                                <button className="button m-2" type="button" onClick={handleAddDietary}>Add Category</button>
                                            )}
                                            {index >= 1 && (
                                                <button className="button m-2" type="button" onClick={() => handleRemoveDietary(index)}>
                                                    Remover
                                                </button>
                                            )}
                                        </div>
                                    ))}

                                </div>
                            )}
                        </div>
                        <button className="button m-2" type="submit">Update Item</button>
                        <Link to="/items"><button className="button cancel m-2" type="button">Cancelar</button></Link>
                        {errorMessage && <p>{errorMessage}</p>}
                    </form>
                </div>
            </div>

        </div>
    );
}

export default EditItem;
