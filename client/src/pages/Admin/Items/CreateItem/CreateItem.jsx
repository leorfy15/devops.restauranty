import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function CreateItem() {
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [description, setDescription] = useState("");
  const [dietaryInformation, setDietaryInformation] = useState("");
  const [availability, setAvailability] = useState(true);
  const [errorMessage, setErrorMessage] = useState(undefined);
  const [dietaryOptions, setDietaryOptions] = useState([]);
  const [file, setFile] = useState(null);
  const [previewSrc, setPreviewSrc] = useState("");
  const [additionalDietaryInfo, setAdditionalDietaryInfo] = useState([]);

  const navigate = useNavigate();

  useEffect(() => {
    // Fetch dietary information options from the database
    axios
      .get(`${url}/api/items/dietary`)
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
  const handleDietaryInfo = (e) => setDietaryInformation(e.target.value);
  const handleAvailability = (e) => setAvailability(e.target.value === "true");

  const onFileChange = (event) => {
    setFile(event.target.files[0]);

    // Show preview
    const fileReader = new FileReader();
    fileReader.readAsDataURL(event.target.files[0]);
    fileReader.onloadend = () => {
      setPreviewSrc(fileReader.result);
    };
  };

  const handleAddDietaryInfo = () => {
    setAdditionalDietaryInfo([...additionalDietaryInfo, ""]);
  };

  const handleAdditionalDietaryInfoChange = (index, value) => {
    const updatedInfo = [...additionalDietaryInfo];
    updatedInfo[index] = value;
    setAdditionalDietaryInfo(updatedInfo);
  };

  const handleRemoveDietaryInfo = (index) => {
    const updatedInfo = [...additionalDietaryInfo];
    updatedInfo.splice(index, 1);
    setAdditionalDietaryInfo(updatedInfo);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Check if all required fields are filled
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
    const requestBody = new FormData();
    requestBody.append("imagem", file);
    requestBody.append("name", name);
    requestBody.append("price", price);
    requestBody.append("availability", availability);
    requestBody.append("description", description);
    requestBody.append("dietaryInformation", dietaryInformation);
    additionalDietaryInfo.forEach((info) => {
      requestBody.append("dietaryInformation", info);
    });

    axios
      .post(`${url}/api/items/items`, requestBody)
      .then((response) => {
        if (response.status === 200) {
          console.log(response.data);
          console.log(`Item Inserted.`);
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
        <h1>Create Item</h1>
        <div className="inputwrap">
          <form onSubmit={handleSubmit}>
            <div>
              <input
                className="forms m-4"
                type="text"
                name="name"
                placeholder="Item Name"
                value={name}
                onChange={handleName}
              />
            </div>
            <div>
              <input
                className="forms"
                type="text"
                name="price"
                placeholder="Price"
                value={price}
                onChange={handlePrice}
                pattern="\d*"
              />
            </div>
            <div>
              <div>
                <textarea
                  className="forms m-4"
                  name="description"
                  placeholder="Description"
                  value={description}
                  onChange={handleDescription}
                />
              </div>
            </div>

            <input
              className="forms mb-4"
              type="file"
              name="imagem"
              accept=".jpeg, .png, .jpg"
              onChange={onFileChange}
            />
            <div>
              {previewSrc ? (<img src={previewSrc} className="images" alt="Preview" />) : null}
            </div>
            <div>
              <input
                type="radio"
                name="availability"
                id="available"
                value="true"
                onChange={handleAvailability}
              />
              <label className="m-2" htmlFor="available">Available</label>
              <input
                type="radio"
                name="availability"
                id="notavailable"
                value="false"
                onChange={handleAvailability}
              />
              <label className="m-2" htmlFor="notavailable">Unavailable</label>
            </div>
            <div>
              <select
                className="forms mt-4"
                name="dietaryinfo"
                value={dietaryInformation}
                onChange={handleDietaryInfo}
              >
                <option value="" disabled>Select a Category</option>
                {dietaryOptions.map((option) => (
                  <option key={option.id} value={option.name}>
                    {option.name} - {option.description}
                  </option>
                ))}
              </select>
              <button className="button w-12 m-2" type="button" onClick={handleAddDietaryInfo}>
                +
              </button>
              <br />

              {additionalDietaryInfo.map((info, index) => (
                <div key={index} className="dietary-info">
                  <select
                    className="forms"
                    name="dietaryinfo"
                    value={info}
                    onChange={(e) =>
                      handleAdditionalDietaryInfoChange(index, e.target.value)
                    }
                  >
                    <option value="" disabled>Select a Category</option>
                    {dietaryOptions.map((option) => (
                      <option key={option.id} value={option.name}>
                        {option.name} - {option.description}
                      </option>
                    ))}
                  </select>

                  <button
                    className="button m-2"
                    type="button"
                    onClick={() => handleRemoveDietaryInfo(index)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
            {errorMessage && <p className="error-message">{errorMessage}</p>}
            <button className="button m-2" type="submit">Create Item</button>

          </form >
        </div>

      </div >
    </div>
  );
}

export default CreateItem;
